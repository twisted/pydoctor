'use strict';


function httpGet(callback, url, mimeType) {   

    var xobj = new XMLHttpRequest();
        xobj.overrideMimeType(mimeType);
    xobj.open('GET', url, true); // Asynchronous
    xobj.send(null);  
    xobj.onload = function () {
        if (xobj.readyState == 4){
            if (xobj.status == "200") {
                callback(xobj.responseText);
            }
            else{
                throw( "Error during the XMLHttpRequest, status: " + xobj.status.toString() ); 
            }
        }
    };
}

function setStatus(message) {
    document.getElementById('search-status').textContent = message;
}



function buildSearchResult(result, documents) {
    // Find the result model 
    const dobj = documents.getElementById(parseInt(result.ref));
    
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
            setStatus("Something went wrong. See development console for details.");
            throw err;
          }
    });
}

async function _search(query) {
    if (!query) {
        setStatus('No search query provided.');
        return;
    }

    // Call lunr.Index.search
    httpGet(function(response) {
        
        // Parse JSON string into object
        let data = JSON.parse(response);
        // https://lunrjs.com/docs/lunr.Index.html
        let lunr_index = lunr.Index.load(data);
        let results = lunr_index.search(query);
        if (!results.length) {
            setStatus('No results matches "' + query + '"');
            return;
        }
        setStatus(
            'Search for "' + query + '" yielded ' + results.length + ' ' +
            (results.length === 1 ? 'result' : 'results') + ':');
        
        // Get result data
        httpGet(function(response2) {
            let parser = new DOMParser();
            let documents = parser.parseFromString(response2, "text/xml");
            let results_list = document.getElementById('search-results');
            
            // Display results
            results.forEach(function (result) {
                results_list.appendChild(buildSearchResult(result, documents));
            });

        }, "all-documents.html", "application/xml");
    }, "searchindex.json", "application/json");
}

setStatus("Searching...");
// Get the query terms
const _query = decodeURIComponent(new URL(window.location).hash.substring(1))
// Setting the search box text to the query
document.getElementById('search-box').value = _query
// Launch the search
search(_query);
