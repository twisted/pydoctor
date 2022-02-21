function setStatus(message) {
  document.getElementById('search-status').textContent = message;
}

function _setInfos(message, box_id, text_id) {
  document.getElementById(text_id).textContent = message;
  if (message.length>0){
    document.getElementById(box_id).style.display = 'block';
  }
  else{
    document.getElementById(box_id).style.display = 'none';
  }
}

function setInfos(message) {
  _setInfos(message, 'search-infos-box', 'search-infos');
}

function setWarning(message) {
  _setInfos(message, 'search-warn-box', 'search-warn');
}

function setErrorStatus() {
  setStatus("Something went wrong.");
}

function setErrorInfos(message) {
  if (message != undefined){
    setWarning("Error: " +  message + ". See development console for details.");
  }
  else{
    setWarning("Error: See development console for details.");
  }
}

function buildSearchResult(dobj) {

  // Build one result item
  var li = document.createElement('li'),
      article = document.createElement('article'),
      header = document.createElement('header'),
      section = document.createElement('section'),
      code = document.createElement('code'),
      a = document.createElement('a'),
      p = document.createElement('p');

  p.innerHTML = dobj.querySelector('.summary').innerHTML;
  a.setAttribute('href', dobj.querySelector('.url').innerHTML);
  a.textContent = dobj.querySelector('.fullName').innerHTML;
  
  let kind_value = dobj.querySelector('.kind').innerHTML;
  let type_value = dobj.querySelector('.type').innerHTML;

  // Adding '()' on functions and methods
  if (type_value.endsWith("Function")){
      a.textContent = a.textContent + '()';
  }
  
  // Putting everything together
  li.appendChild(article);
  article.appendChild(header);
  article.appendChild(section);
  header.appendChild(code);
  code.appendChild(a);
  section.appendChild(p);

  // Set private and kind as the CSS class
  let ob_css_class = dobj.querySelector('.kind').innerHTML.toLowerCase().replace(' ', '');
  if (dobj.querySelector('.privacy').innerHTML.includes('PRIVATE')){
    li.setAttribute('class', 'private ' + ob_css_class);
  }
  else{
    li.setAttribute('class', ob_css_class)
  }

  //Add type metadata in order to be able to filter
  let type_metadata = document.createElement('meta');
  type_metadata.setAttribute('name', 'type');
  type_metadata.setAttribute('class', 'type');
  type_metadata.setAttribute('content', type_value);
  li.appendChild(type_metadata);

  //Add kind metadata in order to be able to filter
  let kind_metadata = document.createElement('meta');
  kind_metadata.setAttribute('name', 'kind');
  kind_metadata.setAttribute('class', 'kind');
  kind_metadata.setAttribute('content', kind_value);
  li.appendChild(kind_metadata);

  return li;
}

function setLongSearchInfos(){
  setWarning("This is taking longer than usual... You can keep waiting for the search to complete, or retry the search with other terms.");
}


//////// SETUP /////////
// Hide the div if the user clicks outside of it

var input = document.getElementById('search-box');
var results_container = document.getElementsByClassName('search-results-container')[0];

input.addEventListener('focus', function() {
  results_container.style.display = 'block';
});

window.addEventListener('load', (event) => {
  results_container.style.display = 'none';
});

// Close the dropdown if the user clicks outside of it
window.addEventListener("click", function(event) {
  if (event && !event.target.closest('.search-results-container') && !event.target.matches('#search-box')){
    results_container.style.display = 'none';
  }
});
results_container.style.display = 'none';
setInfos('')
setWarning('')

///////////////////// SEARCH //////////////////////////

// Setup the search worker   
var worker = new Worker('search-worker.js');
var _setLongSearchInfosTimeout = null;

function search(){

  setInfos('')
  setWarning('')

  setStatus("Searching...")

  httpGet("all-documents.html", function(_r) {})

  let _url = new URL(document.URL);
  console.log(_url);

  
  var _query = null;
  let results_list = document.getElementById('search-results'); 

  // Get the query terms 

  _query = input.value

  if (!_query.length>0){
    setStatus('No search query provided.')
    results_list.innerHTML = '';
    return ;
  }

  console.log("Your query is: "+ _query)

  if (!window.Worker) {
    setStatus("Cannot search: JavaScript Worker API is not supported in your browser. ");
    return ;
  }

  worker.postMessage({
    query: _query,
  });

  // Get result data
  httpGet("all-documents.html", function(all_documents_response) {

    worker.onmessage = function (response) {

      if (_setLongSearchInfosTimeout){
        clearTimeout(_setLongSearchInfosTimeout)
      }
      
      console.log("Message received from worker: ")
      console.dir(response.data)

      if (!response.data.results){
        setErrorStatus();
        throw("No data received from worker")
        results_list.innerHTML = '';
      }

      if (response.data.results.length == 0){
        setStatus('No results matches "' + _query + '"');
        results_list.innerHTML = '';
        return ;
      }
      else{
        setStatus('Building documents...');
      }

      // PARSE DATA FROM HTML DOCUMENT
      let parser = new self.DOMParser();
      let all_documents = parser.parseFromString(all_documents_response, "text/html");
      let search_results_documents = []
      
      results_list.innerHTML = '';
      
      response.data.results.forEach(function (result) {
          // Find the result model 
          var dobj = all_documents.getElementById(result.ref);
          
          if (!dobj){
              setErrorStatus();
              throw ("Cannot find document ID: " + result.ref)
          }
          // Save
          search_results_documents.push(dobj);

          // Display results: edit DOM
          let li = buildSearchResult(dobj);
          results_list.appendChild(li);

      });

      if (response.data.results[0].score <= 7){
        if (response.data.results.length > 500){
          setWarning("Your search yielded a lot of results! and there aren't many great matches. Maybe try with other terms?");
        }
        else{
          setWarning("Unfortunately, it looks like there aren't many great matches for your search. Maybe try with other terms?");
        }
      }
      else {
        if (response.data.results.length > 500){
          setWarning("Your search yielded a lot of results! Maybe try with other terms?");
        }
      }

      let public_search_results = search_results_documents.filter(function(value){
        return !value.querySelector('.privacy').innerHTML.includes("PRIVATE");
      })

      if (public_search_results.length==0){
        setStatus('No results matches "' + _query + '"');
        setInfos('Some private objects matches your search though.');
      }
      else{

        setStatus(
          'Search for "' + _query + '" yielded ' + public_search_results.length + ' ' +
          (public_search_results.length === 1 ? 'result' : 'results') + '.');
      }

      };
    
    worker.onerror = function(error) {
      console.log(error);
      if (_setLongSearchInfosTimeout){
        clearTimeout(_setLongSearchInfosTimeout)
      }
      error.preventDefault();
      setErrorStatus();
      setErrorInfos(error.message);
    }

  },
  function(error){
    console.log(error);
    setErrorStatus();
    setErrorInfos(error.message);
  });
  _setLongSearchInfosTimeout = setTimeout(setLongSearchInfos, 8000);
}

search_function = function(event){
  try{
    worker.terminate()
    if (_setLongSearchInfosTimeout){
      clearTimeout(_setLongSearchInfosTimeout)
    }
    worker = new Worker('search-worker.js');
    search()
  }
  catch (err){
    console.log(err);
    setErrorStatus();
    setErrorInfos(err.message);
  }
};

input.addEventListener('input', search_function);