function setStatus(message) {
  document.getElementById('search-status').textContent = message;
}

function setInfos(message) {
  document.getElementById('search-infos').textContent = message;
  if (message.length>0){
    document.getElementById('search-infos-box').style.display = 'block'
  }
  else{
    document.getElementById('search-infos-box').style.display = 'none'
  }
}

function setPrivateInfos(message) {
  document.getElementById('search-private-infos').textContent = message;
}

function setWarning(message) {
  document.getElementById('search-warn').textContent = message;
  if (message.length>0){
    document.getElementById('search-warn-box').style.display = 'block'
  }
  else{
    document.getElementById('search-warn-box').style.display = 'none'
  }
}

function setErrorStatus() {
  setStatus("Something went wrong.");
}

function setErrorInfos(message) {
  setWarning("Error: " +  message + ". See development console for details.");
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
  let kind_value = dobj.querySelector('.kind').innerHTML
  if (kind_value.includes("Function") || kind_value.includes("Method")){
      a.textContent = a.textContent + '()'
  }
  
  // Putting everything together
  li.appendChild(article);
  article.appendChild(header);
  article.appendChild(section);
  header.appendChild(code);
  code.appendChild(a);
  section.appendChild(p);

  // Set private
  if (dobj.querySelector('.privacy').innerHTML.includes('PRIVATE')){
    li.setAttribute('class', 'private')
  }

  return li
}

function setLongSearchInfos(){
  setWarning("This is taking longer than usual... You can keep waiting for the search to complete, or retry the search with other terms.")
}


function buildInfosString(search_results_documents, priv){

  let nb_classes = search_results_documents.filter(function(value){
    return (value.querySelector('.type').innerHTML.endsWith("Class") && (value.querySelector('.privacy').innerHTML.endsWith(priv ? "PRIVATE" : "VISIBLE")))
  }).length;  

  let nb_methods_or_functions = search_results_documents.filter(function(value){
    return (value.querySelector('.type').innerHTML.endsWith("Function") && (value.querySelector('.privacy').innerHTML.endsWith(priv ? "PRIVATE" : "VISIBLE")))
  }).length;  

  let nb_module_or_package = search_results_documents.filter(function(value){
    return (value.querySelector('.type').innerHTML.endsWith("Module") || value.querySelector('.kind').innerHTML.endsWith("Package")) && (value.querySelector('.privacy').innerHTML.endsWith(priv ? "PRIVATE" : "VISIBLE"))
  }).length;  

  let nb_var = search_results_documents.filter(function(value){
    return (value.querySelector('.type').innerHTML.endsWith("Attribute")) && (value.querySelector('.privacy').innerHTML.endsWith(priv ? "PRIVATE" : "VISIBLE"))

  }).length; 

  return('Including ' + nb_classes.toString() + (priv ? " private" : "") + ' class(es), ' + nb_methods_or_functions.toString() + (priv ? " private" : "") + 
    ' method(s) and/or function(s), ' + nb_module_or_package + (priv ? " private" : "") + ' module(s) and/or package(s) and ' + nb_var + (priv ? " private" : "") + ' attribute(s).')
}

///////////////////// MAIN JS ROUTINE //////////////////////////

function search(){

let _url = new URL(document.URL);
console.log(_url);

var _setLongSearchInfosTimeout = null;
var _query = null;

// Get the query terms
if (!_url.searchParams.has('search-query')){
  setStatus('No search query provided.')
}
else{
  _query = _url.searchParams.get('search-query');

  if (!_query.length>0){
    setStatus('No search query provided.')
  }
  else{

    // Set the search box text to the query terms
    document.getElementById('search-box').value = _query;

    console.log("Your query is: "+ _query)

    if (!window.Worker) {
      setStatus("Cannot search: JavaScript Worker API is not supported in your browser. ")
    }
    else{

      let results_list = document.getElementById('search-results'); 

      setStatus("Searching...")

      // Setup the search worker   
      let worker = new Worker('search-worker.js');

      worker.postMessage({
        query: _query,
      });
      
      worker.onmessage = function (response) {

        if (_setLongSearchInfosTimeout){
          clearTimeout(_setLongSearchInfosTimeout)
        }
        setInfos('')
        setWarning('')
        
        console.log("Message received from worker: ")
        console.dir(response.data)

        if (!response.data.results){
          return;
          // Error will be reported by onerror
        }

        if (response.data.results.length == 0){
          setStatus('No results matches "' + _query + '"');
          return;
        }
        else{
          setStatus('Fetching documents...');
        }

        // Get result data
        httpGet("all-documents.html", function(response2) {
          let parser = new self.DOMParser();
          let all_documents = parser.parseFromString(response2, "text/html");
          let search_results_documents = []
          
          response.data.results.forEach(function (result) {
              // Find the result model 
              var dobj = all_documents.getElementById(result.ref);
              
              if (!dobj){
                  throw ("Cannot find document ID: " + result.ref)
              }
              // Save
              search_results_documents.push(dobj)

              // Display results: edit DOM
              let li = buildSearchResult(dobj);
              results_list.appendChild(li);

          });

          if (response.data.results[0].score <= 15){
            setWarning("Unfortunately, it looks like there aren't many great matches for your search.")
          }

          let public_search_results = search_results_documents.filter(function(value){
            return !value.querySelector('.privacy').innerHTML.includes("PRIVATE")
          })

          if (public_search_results.length==0){
            setStatus('No results matches "' + _query + '"');
            setInfos('Some private objects matches your search though.')
          }
          else{

            setStatus(
              'Search for "' + _query + '" yielded ' + public_search_results.length + ' ' +
              (public_search_results.length === 1 ? 'result' : 'results') + '.');

            // Build complementary information string

            setInfos(buildInfosString(search_results_documents, false))
          }

          // Build PRIVATE complementary information string

          setPrivateInfos(buildInfosString(search_results_documents, true))

        },
        function(error){
          setErrorStatus();
          setErrorInfos(error.message);
      });

      };

      worker.onerror = function(error) {
        console.log(error)
        if (_setLongSearchInfosTimeout){
          clearTimeout(_setLongSearchInfosTimeout)
        }
        error.preventDefault();
        setErrorStatus();
        setErrorInfos(error.message);
      }


      _setLongSearchInfosTimeout = setTimeout(setLongSearchInfos, 8000)
    }
  }
}

}

search()
