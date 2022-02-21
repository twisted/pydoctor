// Try very hard to import these scripts (5 times). This avoid random errors: 
// Uncaught NetworkError: Failed to execute 'importScripts' on 'WorkerGlobalScope': 
//  The script at 'https://pydoctor--500.org.readthedocs.build/en/500/api/lunr.js' failed to load.

for (let i = 0; i < 5; i++) {
    try{
        importScripts('lunr.js', 'ajax.js'); 
        break;
    } catch (ex){
        if (i<5) {continue;}
        else {throw ex}
    }
}
onmessage = function (message) { // -> {'results': [lunr results]}
    console.log("Message received from main script: ");
    console.dir(message.data)
    
    if (!message.data.query) {
        throw ('No search query provided.');
    }

    // Launch the search

    // Build lunr index from serialized JSON constructed while generating the documentation. 
    httpGet("searchindex.json", function(response) {

        // Parse JSON string into object
        let data = JSON.parse(response);
        
        // Call lunr.Index.search
        // https://lunrjs.com/docs/lunr.Index.html
        let lunr_index = lunr.Index.load(data);
        let search_results = lunr_index.search(message.data.query);
        postMessage({'results':search_results});

        }, function(error){
            throw ('Cannot load the search index: ' + error.message);
        });

  };
