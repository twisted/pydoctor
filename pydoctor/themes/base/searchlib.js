// Wrapper around lunr index searching system for pydoctor API objects 
//      and function to format search results items into rederable HTML elements.
// This file is meant to be used as a library for the pydoctor search bar (search.js) as well as
//      provide a hackable inferface to integrate API docs searching into other platforms, i.e. provide a 
//      "Search in API docs" option from Read The Docs search page.
// Depends on ajax.js, bundled with pydoctor. 
// Other required ressources like lunr.js, searchindex.json and all-documents.html are passed as URL
//      to functions. This makes the code reusable outside of pydoctor build directory.    
// Implementation note: Searches are designed to be launched synchronously, if lunrSearch() is called sucessively (while already running),
// old promise will never resolves and the search worker will be restarted.

// Hacky way to make the worker code inline with the rest of the source file handling the search.
// Worker message params are the following: 
// - query: string
// - indexJSONData: dict
// - defaultFields: list of strings
let _lunrWorkerCode = `

// The lunr.js code will be inserted here.

// ============================================================================
// Implement a queryWithLimit() with MinHeap
// ============================================================================
// A min-heap implementation for efficiently maintaining the top-k results
// during search. This prevents the need to sort all results when only a
// limited number are needed.
lunr.MinHeap = function (maxSize) {
  this.maxSize = maxSize
  this.items = []
}

lunr.MinHeap.prototype.push = function (item) {
  if (this.items.length < this.maxSize) {
    this.items.push(item)
    this._bubbleUp(this.items.length - 1)
  } else if (item.score > this.items[0].score) {
    this.items[0] = item
    this._bubbleDown(0)
  }
}

lunr.MinHeap.prototype._bubbleUp = function (index) {
  if (index === 0) return
  var parentIndex = Math.floor((index - 1) / 2)
  if (this.items[index].score < this.items[parentIndex].score) {
    var temp = this.items[index]
    this.items[index] = this.items[parentIndex]
    this.items[parentIndex] = temp
    this._bubbleUp(parentIndex)
  }
}

lunr.MinHeap.prototype._bubbleDown = function (index) {
  var leftChildIndex = 2 * index + 1
  var rightChildIndex = 2 * index + 2
  var smallestIndex = index

  if (
    leftChildIndex < this.items.length &&
    this.items[leftChildIndex].score < this.items[smallestIndex].score
  ) {
    smallestIndex = leftChildIndex
  }

  if (
    rightChildIndex < this.items.length &&
    this.items[rightChildIndex].score < this.items[smallestIndex].score
  ) {
    smallestIndex = rightChildIndex
  }

  if (smallestIndex !== index) {
    var temp = this.items[index]
    this.items[index] = this.items[smallestIndex]
    this.items[smallestIndex] = temp
    this._bubbleDown(smallestIndex)
  }
}

lunr.MinHeap.prototype.toSortedArray = function () {
  return this.items.slice().sort(function (a, b) {
    return b.score - a.score
  })
}

// Performs a query against the index with a limit on the number of results returned.
// This is a performance-optimized version of the query method that uses a min-heap
// to maintain only the top-k results, with early exit optimizations to skip low-scoring
// documents when the result set is full.
// When limit is -1, this method behaves identically to the original query() method.
lunr.Index.prototype.queryWithLimit = function (fn, limit) {
  if (limit === undefined) {
    throw new Error('queryWithLimit requires a limit parameter. Use -1 for unlimited results.')
  }

  if (limit === -1) {
    return this.query(fn)
  }

  if (typeof limit !== 'number' || limit <= 0 || Math.floor(limit) !== limit) {
    throw new Error('limit must be a positive integer or -1 for unlimited results')
  }

  var query = new lunr.Query(this.fields),
      matchingFields = Object.create(null),
      queryVectors = Object.create(null),
      termFieldCache = Object.create(null),
      requiredMatches = Object.create(null),
      prohibitedMatches = Object.create(null)

  for (var i = 0; i < this.fields.length; i++) {
    queryVectors[this.fields[i]] = new lunr.Vector
  }

  fn.call(query, query)

  for (var i = 0; i < query.clauses.length; i++) {
    var clause = query.clauses[i],
        terms = null,
        clauseMatches = lunr.Set.empty

    if (clause.usePipeline) {
      terms = this.pipeline.runString(clause.term, {
        fields: clause.fields
      })
    } else {
      terms = [clause.term]
    }

    for (var m = 0; m < terms.length; m++) {
      var term = terms[m]
      clause.term = term

      var termTokenSet = lunr.TokenSet.fromClause(clause),
          expandedTerms = this.tokenSet.intersect(termTokenSet).toArray()

      if (expandedTerms.length === 0 && clause.presence === lunr.Query.presence.REQUIRED) {
        for (var k = 0; k < clause.fields.length; k++) {
          var field = clause.fields[k]
          requiredMatches[field] = lunr.Set.empty
        }
        break
      }

      for (var j = 0; j < expandedTerms.length; j++) {
        var expandedTerm = expandedTerms[j],
            posting = this.invertedIndex[expandedTerm],
            termIndex = posting._index

        for (var k = 0; k < clause.fields.length; k++) {
          var field = clause.fields[k],
              fieldPosting = posting[field],
              matchingDocumentRefs = Object.keys(fieldPosting),
              termField = expandedTerm + "/" + field,
              matchingDocumentsSet = new lunr.Set(matchingDocumentRefs)

          if (clause.presence == lunr.Query.presence.REQUIRED) {
            clauseMatches = clauseMatches.union(matchingDocumentsSet)
            if (requiredMatches[field] === undefined) {
              requiredMatches[field] = lunr.Set.complete
            }
          }

          if (clause.presence == lunr.Query.presence.PROHIBITED) {
            if (prohibitedMatches[field] === undefined) {
              prohibitedMatches[field] = lunr.Set.empty
            }
            prohibitedMatches[field] = prohibitedMatches[field].union(matchingDocumentsSet)
            continue
          }

          queryVectors[field].upsert(termIndex, clause.boost, function (a, b) { return a + b })

          if (termFieldCache[termField]) {
            continue
          }

          for (var l = 0; l < matchingDocumentRefs.length; l++) {
            var matchingDocumentRef = matchingDocumentRefs[l],
                matchingFieldRef = new lunr.FieldRef (matchingDocumentRef, field),
                metadata = fieldPosting[matchingDocumentRef],
                fieldMatch

            if ((fieldMatch = matchingFields[matchingFieldRef]) === undefined) {
              matchingFields[matchingFieldRef] = new lunr.MatchData (expandedTerm, field, metadata)
            } else {
              fieldMatch.add(expandedTerm, field, metadata)
            }
          }

          termFieldCache[termField] = true
        }
      }
    }

    if (clause.presence === lunr.Query.presence.REQUIRED) {
      for (var k = 0; k < clause.fields.length; k++) {
        var field = clause.fields[k]
        requiredMatches[field] = requiredMatches[field].intersect(clauseMatches)
      }
    }
  }

  var allRequiredMatches = lunr.Set.complete,
      allProhibitedMatches = lunr.Set.empty

  for (var i = 0; i < this.fields.length; i++) {
    var field = this.fields[i]

    if (requiredMatches[field]) {
      allRequiredMatches = allRequiredMatches.intersect(requiredMatches[field])
    }

    if (prohibitedMatches[field]) {
      allProhibitedMatches = allProhibitedMatches.union(prohibitedMatches[field])
    }
  }

  var matchingFieldRefs = Object.keys(matchingFields),
      results = new lunr.MinHeap(limit),
      matches = Object.create(null)

  if (query.isNegated()) {
    matchingFieldRefs = Object.keys(this.fieldVectors)
    for (var i = 0; i < matchingFieldRefs.length; i++) {
      var matchingFieldRef = matchingFieldRefs[i]
      var fieldRef = lunr.FieldRef.fromString(matchingFieldRef)
      matchingFields[matchingFieldRef] = new lunr.MatchData
    }
  }

  // OPTIMIZATION: Early exit threshold - skip documents that can't beat the current minimum
  // Once the heap is full, we only need to check if a score is higher than the heap's minimum
  for (var i = 0; i < matchingFieldRefs.length; i++) {
    var fieldRef = lunr.FieldRef.fromString(matchingFieldRefs[i]),
        docRef = fieldRef.docRef

    if (!allRequiredMatches.contains(docRef)) {
      continue
    }

    if (allProhibitedMatches.contains(docRef)) {
      continue
    }

    var fieldVector = this.fieldVectors[fieldRef],
        score = queryVectors[fieldRef.fieldName].similarity(fieldVector),
        docMatch

    // OPTIMIZATION: If heap is full and this score won't beat the minimum, skip it
    if (results.items.length === limit && score <= results.items[0].score) {
      continue
    }

    if ((docMatch = matches[docRef]) !== undefined) {
      docMatch.score += score
      docMatch.matchData.combine(matchingFields[fieldRef])
    } else {
      var match = {
        ref: docRef,
        score: score,
        matchData: matchingFields[fieldRef]
      }
      matches[docRef] = match
      results.push(match)
    }
  }

  return results.toSortedArray()
}
// ============================================================================

onmessage = (message) => {
    if (!message.data.query) {
        throw new Error('No search query provided.');
    }
    if (!message.data.indexJSONData) {
        throw new Error('No index data provided.');
    }
    if (!message.data.defaultFields) {
        throw new Error('No default fields provided.');
    }
    if (!message.data.limit) {
        throw new Error('No valid limit provided.');
    }

    // Create index
    let index = lunr.Index.load(message.data.indexJSONData);

    // Declare query function building 
    function _queryfn(_query){ // _query is the Query object
        // Edit the parsed query clauses that are applicable for all fields (default) in order
        // to remove the field 'kind' from the clause since this it's only useful when specifically requested.
        var parser = new lunr.QueryParser(message.data.query, _query)
        parser.parse()

        _query.clauses.forEach(clause => {
            if (clause.fields == _query.allFields){
                // we change the query fields when they are applicable to all fields
                // to a list of predefined fields because we might include additional filters (like kind:)
                // which should not be matched by default.
                clause.fields = message.data.defaultFields;
            }

        });
        // Auto wilcard feature, see issue https://github.com/twisted/pydoctor/issues/648
        _query.clauses.forEach(clause => {
            let excplicitlyOptional = clause.term.slice(0,1) == '?' && clause.term.length > 1;
            if (excplicitlyOptional){
                // Remove leading '?' from term
                clause.term = clause.term.slice(1);
            }

            if (clause.presence === lunr.Query.presence.OPTIONAL) { // ignore clauses that have explicit presence (+/-)
                if (!excplicitlyOptional){
                    clause.presence = lunr.Query.presence.REQUIRED
                }
                // Setting clause.wildcard is useless (but we do it anyway for clarty), 
                // due to https://github.com/olivernn/lunr.js/issues/495
                // But appending to .term works...
                if (clause.term.slice(-1) != '*'){
                    // Adding a trailing wildcard
                    clause.wildcard = lunr.Query.wildcard.TRAILING
                    clause.term = clause.term + '*'
                }
                
                if (clause.term.indexOf('.') != -1) {
                    if (clause.term.slice(0,1) != '*'){
                        // Adding a leading wildcard if the dot is included as well.
                        clause.wildcard = lunr.Query.wildcard.LEADING | lunr.Query.wildcard.TRAILING
                        clause.term = '*' + clause.term
                    }
                }
            }
        });

        console.log('Parsed query:')
        console.dir(_query)
    }

    // Launch the search
    var results = index.queryWithLimit(_queryfn, message.data.limit)

    // Post message with results
      postMessage({'results':results});
};
`;

// Adapted from https://stackoverflow.com/a/44137284
// Override worker methods to detect termination and count message posting and restart() method.
// This allows some optimizations since the worker doesn't need to be restarted when it hasn't been used.
function _makeWorkerSmart(workerURL) {
    // make normal worker
    var worker = new Worker(workerURL);
    // assume that it's running from the start
    worker.terminated = false;
    worker.postMessageCount = 0;
    // count the number of times postMessage() is called
    worker.postMessage = function() {
        this.postMessageCount = this.postMessageCount + 1;
        // normal post message
        return Worker.prototype.postMessage.apply(this, arguments);
    }
    // sets terminated to true
    worker.terminate = function() {
        if (this.terminated===true){return;}
        this.terminated = true;
        // normal terminate
        return Worker.prototype.terminate.apply(this, arguments);
    }
    // creates NEW WORKER with the same URL as itself, terminate worker first.
    worker.restart = function() {
        this.terminate();
        return _makeWorkerSmart(workerURL);
    }
    return worker;
}

var _searchWorker = null

/**
 * The searchEventsEnv Document variable let's let caller register a event listener "searchStarted" for sending
 * a signal when the search actually starts, could be up to 0.2 or 0.3 secs ater user finished typing.
 */
let searchEventsEnv = document.implementation.createHTMLDocument(
    'This is a document to popagate search related events, we avoid using "document" for performance reasons.');

// there is a difference in abortSearch() vs restartSearchWorker().
// abortSearch() triggers a abortSearch event, which have a effect on searches that are not yet running in workers.
// whereas restartSearchWorker() which kills the worker if it's in use, but does not abort search that is not yet posted to the worker.
function abortSearch(){
    searchEventsEnv.dispatchEvent(new CustomEvent('abortSearch', {}));
}
// Kills and restarts search worker (if needed).
function restartSearchWorker() {
    var w = _searchWorker;
    if (w!=null){
        if (w.postMessageCount>0){
            // the worker has been used, it has to be restarted
            // TODO: Actually it needs to be restarted only if it's running a search right now.
            // Otherwise we can reuse the same worker, but that's not a very big deal in this context.
            w = w.restart();
        } 
        // Else, the worker has never been used, it can be returned as is. 
        // This can happens when typing fast with a very large index JSON to load.
    }
    _searchWorker = w;
}

function _getWorkerPromise(lunJsSourceCode){ // -> Promise of a fresh worker to run a query.
    let promise = new Promise((resolve, reject) => {
        // Do the search business, wrap the process inside an inline Worker.
        // This is a hack such that the UI can refresh during the search.
        if (_searchWorker===null){
            // Create only one blob and URL.
            let lunrWorkerCode = lunJsSourceCode + _lunrWorkerCode;
            let _workerBlob = new Blob([lunrWorkerCode], {type: 'text/javascript'});
            let _workerObjectURL = window.URL.createObjectURL(_workerBlob);
            _searchWorker = _makeWorkerSmart(_workerObjectURL)
        }
        else{
            restartSearchWorker();
        }
        resolve(_searchWorker);
    });
    return promise
}

/**
 * Launch a search and get a promise of results. One search can be lauch at a time only.
 * Old promise never resolves if calling lunrSearch() again while already running.
 * @param query: Query string.
 * @param indexURL: URL pointing to the Lunr search index, generated by pydoctor.
 * @param defaultFields: List of strings: default fields to apply to query clauses when none is specified. ["name", "names", "qname"] for instance.
 * @param lunrJsURL: URL pointing to a copy of lunr.js.
 * @param searchDelay: Number of miliseconds to wait before actually launching the query. This is useful to set for "search as you type" kind of search box
 *                     because it let a chance to users to continue typing without triggering useless searches (because previous search is aborted on launching a new one).
 * @param limit: Maximum number of results to return. If -1, returns all results.
*/
function lunrSearch(query, indexURL, defaultFields, lunrJsURL, searchDelay, limit = -1){
    // Abort ongoing search
    abortSearch();

    // Register abort procedure.
    var _aborted = false;
    searchEventsEnv.addEventListener('abortSearch', (ev) => {
        _aborted = true;
        searchEventsEnv.removeEventListener('abortSearch', this);
    });

    // Perf:
    // Because this function can be called a lot of times in a very few moments, 
    // Actually launch search after a delay to let a chance to users to continue typing,
    // which would trigger a search abort event, which would avoid wasting a worker 
    // for a search that is not wanted anymore.
    return new Promise((_resolve, _reject) => {
        setTimeout(() => {
        _resolve(
        _getIndexDataPromise(indexURL).then((lunrIndexData) => {
        // Include lunr.js source inside the worker such that it has no dependencies.
        return httpGetPromise(lunrJsURL).then((responseText) => {
        // Do the search business, wrap the process inside an inline Worker.
        // This is a hack such that the UI can refresh during the search.
        return _getWorkerPromise(responseText).then((worker) => {
            let promise = new Promise((resolve, reject) => {
                worker.onmessage = (message) => {
                    if (!message.data.results){
                        reject("No data received from worker");
                    }
                    else{
                        console.log("Got result from worker:")
                        console.dir(message.data.results)
                        resolve(message.data.results)
                    }
                }
                worker.onerror = function(error) {
                    reject(error);
                };
            });
            let _msgData = {
                'query': query,
                'indexJSONData': lunrIndexData,
                'defaultFields': defaultFields,
                'limit': limit,
            }
            
            if (!_aborted){
                console.log(`Posting query "${query}" to worker:`)
                console.dir(_msgData)
                worker.postMessage(_msgData);
                searchEventsEnv.dispatchEvent(
                    new CustomEvent("searchStarted", {'query':query})
                );
            }

            return promise
        });
        });
        })
        );}, searchDelay);
    });
}

/** 
* @param results: list of lunr.Index~Result.
* @param allDocumentsURL: URL pointing to all-documents.html, generated by pydoctor.
* @returns: Promise of a list of HTMLElement corresponding to the all-documents.html
*   list elements matching your search results.
*/
function fetchResultsData(results, allDocumentsURL){
    return _getAllDocumentsPromise(allDocumentsURL).then((allDocuments) => {
        // Look for results data in parsed all-documents.html
        return _asyncFor(results, (result) => {
            // Find the result model row data.
            var dobj = allDocuments.getElementById(result.ref);
            if (!dobj){
                throw new Error("Cannot find document ID: " + result.ref);
            }
            // Return result data
            return dobj;
        })
    })
}

/**
 * Transform list item as in all-documents.html into a formatted search result row.
 */
function buildSearchResult(dobj) {

    // Build one result item
    var tr = document.createElement('tr'),
        kindtd = document.createElement('td'),
        contenttd = document.createElement('td'),
        article = document.createElement('article'),
        header = document.createElement('header'),
        section = document.createElement('section'),
        code = document.createElement('code'),
        a = document.createElement('a'),
        p = document.createElement('p');
  
    p.innerHTML = dobj.querySelector('.summary').innerHTML;
    a.setAttribute('href', dobj.querySelector('.url').innerHTML);
    a.setAttribute('class', 'internal-link');
    a.innerHTML = dobj.querySelector('.fullName').innerHTML;
    
    let kind_value = dobj.querySelector('.kind').innerHTML;
    let type_value = dobj.querySelector('.type').innerHTML;
  
    // Adding '()' on functions and methods
    if (type_value.endsWith("Function")){
        a.innerHTML = a.innerHTML + '()';
    }
  
    kindtd.innerHTML = kind_value;
    
    // Putting everything together
    tr.appendChild(kindtd);
    tr.appendChild(contenttd);
    contenttd.appendChild(article);
    article.appendChild(header);
    article.appendChild(section);
    header.appendChild(code);
    code.appendChild(a);
    section.appendChild(p);
  
    // Set kind as the CSS class of the kind td tag
    let ob_css_class = dobj.querySelector('.kind').innerHTML.toLowerCase().replace(' ', '');
    kindtd.setAttribute('class', ob_css_class);
  
    // Set private
    if (dobj.querySelector('.privacy').innerHTML.includes('PRIVATE')){
      tr.setAttribute('class', 'private');
    }
    
    return tr;
}


// This gives the UI the opportunity to refresh while we're iterating over a large list.
function _asyncFor(iterable, callback) { // -> Promise of List of results returned by callback
    const promise_global = new Promise((resolve_global, reject_global) => {
      let promises = [];
      iterable.forEach((element) => {
          promises.push(new Promise((resolve, _reject) => {
            setTimeout(() => {
                try{ resolve(callback(element)); }
                catch (error){ _reject(error); }
            }, 0);
          }));
      }); 
      Promise.all(promises).then((results) =>{
        resolve_global(results);
      }).catch((err) => {
          reject_global(err);
      });
    });
    return promise_global;
  }

// Cache indexes JSON data since it takes a little bit of time to load JSON into stuctured data
var _indexDataCache = {};
function _getIndexDataPromise(indexURL) { // -> Promise of a structured data for the lunr Index.
    if (!_indexDataCache[indexURL]){
        return httpGetPromise(indexURL).then((responseText) => {
            _indexDataCache[indexURL] = JSON.parse(responseText)
            return (_indexDataCache[indexURL]);
        });
    }
    else{
        return new Promise((_resolve, _reject) => {
            _resolve(_indexDataCache[indexURL]);
        });
    }
}

// Cache Document object
var _allDocumentsCache = {};
function _getAllDocumentsPromise(allDocumentsURL) { // -> Promise of the all-documents.html Document object.
    if (!_allDocumentsCache[allDocumentsURL]){
        return httpGetPromise(allDocumentsURL).then((responseText) => {
            let _parser = new self.DOMParser();
            _allDocumentsCache[allDocumentsURL] = _parser.parseFromString(responseText, "text/html");
            return (_allDocumentsCache[allDocumentsURL]);
        });
    }
    else{
        return new Promise((_resolve, _reject) => {
            _resolve(_allDocumentsCache[allDocumentsURL]);
        });
    }
}
