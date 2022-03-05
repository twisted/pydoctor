// Wrapper around lunr index searching system for pydoctor API objects 
//      and function to format search results items into rederable HTML elements.
// This file is meant to be used as a library for the pydoctor search bar (search.js) as well as
//      provide a hackable inferface to integrate API docs searching into other platforms, i.e. provide a 
//      "Search in API docs" option from Read The Docs search page.
// Depends on ajax.js, bundled with pydoctor.

// Hacky wat to make the worker code inline with the rest of the source file hadling search.
// Worker message params are the following: 
// - query: string
// - indexJSONData: dict
// - defaultFields: list of strings

let _lunrWorkerCode = `

// The lunr.js code will be inserted here.

onmessage = (message) => {
    if (!message.data.query) {
        throw ('No search query provided.');
    }
    if (!message.data.indexJSONData) {
        throw ('No index data provided.');
    }
    if (!message.data.defaultFields) {
        throw ('No default fields provided.');
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
                // By default, for small index searches, only search on name fields
                clause.fields = message.data.defaultFields;
            }
            // TODO: If fuzzy match is greater than 20 throw an error.
        });
    }

    // Launch the search
    let results = index.query(_queryfn)
    
    // Post message with results
    postMessage({'results':results});
};
`;

var _workerBlob = null;
var _worker = null
/**
 * Launch a search and get a promise of results.
 * @param query: Query string.
 * @param indexURL: Lunr search index URL.
 * @param defaultFields: List of strings: default fields to apply to query clauses when none is specified. ["name", "names", "qname"] for instance.
 * @param lunrJsURL: URL where we can find a copy of lunr.js.
 */
function lunrSearch(query, indexURL, defaultFields, lunrJsURL){

    return _getIndexDataPromise(indexURL).then((lunrIndexData) => {
        // Include lunr.js source inside the worker such that it has no dependencies.
        return httpGetPromise(lunrJsURL).then((responseText) => {
            // Do the search business, wrap the process inside an inline Worker.
            // This is a hack such that the UI can refresh during the search.
            if (_workerBlob===null){
                // Create only one blob
                let lunrWorkerCode = responseText + _lunrWorkerCode;
                _workerBlob = new Blob([lunrWorkerCode], {type: 'text/javascript'});
            }
            if (_worker!=null){
                _worker.terminate()
            }
            
            _worker = new Worker(window.URL.createObjectURL(_workerBlob));
            let promise = new Promise((resolve, reject) => {
                _worker.onmessage = (message) => {
                    if (!message.data.results){
                        reject("No data received from worker");
                    }
                    else{
                        console.log("Got result from worker:")
                        console.dir(message.data.results)
                        resolve(message.data.results)
                    }
                }
                _worker.onerror = function(error) {
                    reject(error);
                };
            });
            _msg_data = {
                'query': query,
                'indexJSONData': lunrIndexData,
                'defaultFields': defaultFields
            }
            console.log("Posting query to worker:")
            console.dir(_msg_data)
            _worker.postMessage(_msg_data);
            return promise
        });
    });
}

/** 
* @param results: list of lunr.Index~Result.
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
                throw ("Cannot find document ID: " + result.ref);
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
    a.textContent = dobj.querySelector('.fullName').innerHTML;
    
    let kind_value = dobj.querySelector('.kind').innerHTML;
    let type_value = dobj.querySelector('.type').innerHTML;
  
    // Adding '()' on functions and methods
    if (type_value.endsWith("Function")){
        a.textContent = a.textContent + '()';
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
    const promise_global = new Promise((resolve_global, _reject) => {
      let promises = [];
      iterable.forEach((element) => {
          promises.push(new Promise((resolve, _reject) => {
            setTimeout(() => {
              resolve(callback(element));
            }, 0);
          }));
      }); 
      Promise.all(promises).then((results) =>{
        resolve_global(results);
      });
    });
    return promise_global;
  }

// Cache indexes JSON data since it takes a little bit if time to load JSON into stuctured data
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
        }, (error) => {
            _reject(error);
        });
    }
}

// Cache Document object
var _allDocumentsCache = {};
function _getAllDocumentsPromise(allDocumentsURL) { // -> Promise of a Document object.
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
        }, (error) => {
            _reject(error);
        });
    }
}