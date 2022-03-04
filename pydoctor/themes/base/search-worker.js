// Try very hard to import these scripts (5 times). This avoid random errors: 
// Uncaught NetworkError: Failed to execute 'importScripts' on 'WorkerGlobalScope': 
// The script at 'https://pydoctor--500.org.readthedocs.build/en/500/api/lunr.js' failed to load.

for (let i = 0; i < 5; i++) {
    try{
        importScripts('lunr.js', 'ajax.js'); 
        break;
    } catch (ex){
        if (i<5) {continue;}
        else {throw ex;}
    }
}

// Build lunr index from serialized JSON constructed while generating the documentation. 
// Build both indexes as soon as possible with Promises.
// (When new Promise is created, the executor runs automatically)

function getIndexPromise(indexurl) { // -> Promise of a lunr.Index
    return new Promise((_resolve, _reject) => {
        httpGet(indexurl, 
            function(response) {
                // Parse JSON string into object
                let data = JSON.parse(response);
                
                // Call lunr.Index.search
                // https://lunrjs.com/docs/lunr.Index.html
                let lunr_index = lunr.Index.load(data);

                _resolve(lunr_index)
            },
            function(error) {
                _reject('Cannot load the search index: ' + error.message);
            }
        );
    });
}

// A Promise of a lunr.Index with name fields only
const promiseDefaultIndex = getIndexPromise("searchindex.json");
// A Promise of a lunr.Index with all fields
// fullsearchindex.json includes field 'docstring', whereas searchindex.json.
const promiseFullIndex = getIndexPromise("fullsearchindex.json");

onmessage = function (message) { // -> {'results': [lunr results]}
    console.log("Message received from main script: ");
    console.dir(message.data);
    
    if (!message.data.query) {
        throw ('No search query provided.');
    }
    if (!message.data.indextype) {
        throw ('No index type provided.');
    }

    var indexPromise = message.data.indextype === 'full' ?  promiseFullIndex : promiseDefaultIndex;

    // Launch the search
    indexPromise.then((lunr_index) => {
        // Edit the parsed query clauses that are applicable for all fields (default) in order
        // to remove the field 'kind' from the clause since this is only useful when specifically requested.
        let query_fn = function (query) {
            var parser = new lunr.QueryParser(message.data.query, query)
            parser.parse()
            query.clauses.forEach(clause => {
                if (clause.fields == query.allFields){
                    if (message.data.indextype === 'full'){
                        // By default, for full index searches, only search on those 3 fields.
                        clause.fields = ["name", "names", "qname", "docstring"];
                    }
                    else{
                        // By default, for small index searches, only search on those 2 fields.
                        clause.fields = ["name", "names", "qname"];
                    }
                }
            });
        }
        let search_results = lunr_index.query(query_fn);
        postMessage({'results':search_results});
    
    }).catch((error) => {
        throw error;
    });
  };
