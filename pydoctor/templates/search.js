'use strict';


function httpGet(callback, url) {   

    var xobj = new XMLHttpRequest();
    xobj.open('GET', url, true); // Asynchronous
    
    xobj.onload = function () {
        if (xobj.status == "200") {
            callback(xobj.responseText);
        }
        else{
            setErrorStatus()
            throw( "HTTP Error during the XMLHttpRequest, status: " + xobj.status.toString() ); 
        }
    };

    xobj.onerror = function () {
        setErrorStatus()
    };

    xobj.send(null);  
}

function setStatus(message) {
    document.getElementById('search-status').textContent = message;
}

function setErrorStatus() {
    setStatus("Something went wrong. See development console for details.");
}

function buildSearchResult(dobj) {
    
    
    // Build one result item
    var li = document.createElement('li'),
        article = document.createElement('article'),
        header = document.createElement('header'),
        section = document.createElement('section'),
        code = document.createElement('code'),
        a = document.createElement('a'),
        p = document.createElement('p')

    p.innerHTML = dobj.querySelector('.summary').innerHTML;
    a.setAttribute('href', dobj.querySelector('.url').innerHTML);
    a.textContent = dobj.querySelector('.fullName').innerHTML;
    
    // Adding '()' on functions and methods
    if (["Function", "Method"].indexOf(dobj.querySelector('.kind').innerHTML) != -1){
        a.textContent = a.textContent + '()'
    }
    
    // Putting everything together
    li.appendChild(article);
    article.appendChild(header);
    article.appendChild(section);
    header.appendChild(code);
    code.appendChild(a);
    section.appendChild(p);

    return li
  }

function search(query) {
    
    _search(query).catch(err => {
        if (err instanceof lunr.QueryParseError) {
            setStatus(e.message);
            return;
          } else {
            setErrorStatus()
            throw err;
          }
    });
}

async function _search(query) {
    if (!query) {
        setStatus('No search query provided.');
        return;
    }

    httpGet(function(response) {
        
        // Parse JSON string into object
        let data = JSON.parse(response);
        // https://lunrjs.com/docs/lunr.Index.html
        let lunr_index = lunr.Index.load(data);
        // Call lunr.Index.search
        let results = lunr_index.search(query);
        if (!results.length) {
            setStatus('No results matches "' + query + '"');
            return;
        }
        
        // Get result data
        httpGet(function(response2) {
            let parser = new DOMParser();
            let all_documents = parser.parseFromString(response2, "text/html");
            let results_list = document.getElementById('search-results');

            setStatus('Loading...');
            
            // Display results
            results.forEach(function (result) {
                // Find the result model 
                let dobj = all_documents.getElementById(result.ref);

                if (!dobj){
                    setErrorStatus()
                    throw( "Cannot find document ID: " + result.ref ); 
                }

                let li = buildSearchResult(dobj)
                results_list.appendChild(li);

            });

            setStatus(
                'Search for "' + query + '" yielded ' + results.length + ' ' +
                (results.length === 1 ? 'result' : 'results') + ':');

        }, "all-documents.html");
    }, "searchindex.json");

}

setStatus("Searching...");
// Get the query terms
const _query = decodeURIComponent(new URL(window.location).hash.substring(1))
// Setting the search box text to the query
document.getElementById('search-box').value = _query
// Launch the search
search(_query);
