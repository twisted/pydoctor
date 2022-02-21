importScripts('lunr.js', 'ajax.js'); 

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
