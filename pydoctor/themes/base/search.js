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
  return li;
}

function setLongSearchInfos(){
  setWarning("This is taking longer than usual... You can keep waiting for the search to complete, or retry the search with other terms.");
}


//////// SETUP /////////
// Hide the div if the user clicks outside of it

var input = document.getElementById('search-box');
var results_container = document.getElementsByClassName('search-results-container')[0];
let results_list = document.getElementById('search-results'); 

function hideResultContainer(){
  results_container.style.display = 'none';
  if (!document.body.classList.contains("search-help-hidden")){
    document.body.classList.add("search-help-hidden")
  }
}

function showResultContainer(){
  results_container.style.display = 'block';
}

window.addEventListener('load', (event) => {
  hideResultContainer();
});

// Close the dropdown if the user clicks outside of it
window.addEventListener("click", function(event) {
  if (event){
      if (!event.target.closest('.search-results-container') 
          && !event.target.closest('#search-box')
          && !event.target.closest('#search-help-button')){
            hideResultContainer()
            return;
      }
      if (event.target.closest('#search-box')){
        if (input.value.length>0){
          showResultContainer()
        }
      }
  }
});

function toggleSearchHelpText() {
  document.body.classList.toggle("search-help-hidden");
  if (document.body.classList.contains("search-help-hidden") && input.value.length==0){
    hideResultContainer()
  }
  else{
    showResultContainer()
  }
}
// Init search and help text
document.getElementById('search-box-container').style.display = 'block';
document.getElementById('search-help-box').style.display = 'block';
document.body.classList.add("search-help-hidden");


///////////////////// SEARCH //////////////////////////

// Setup the search worker   
var worker = new Worker('search-worker.js');
var _setLongSearchInfosTimeout = null;

function resetLongSearchTimerInfo(){
  if (_setLongSearchInfosTimeout){
    clearTimeout(_setLongSearchInfosTimeout)
  }
}

function resetResultList(){
  results_list.innerHTML = '';
}

function clearSearch(){
  hideResultContainer()
  resetResultList()
  setWarning('')
  setStatus('')
  setInfos('')

  input.value = '';
  showHideClearSearchBtn()
}

function search(){

  setInfos('')
  setWarning('')
  showResultContainer()
  setStatus("Searching...")

  // Get the query terms 

  let _query = input.value

  if (!_query.length>0){
    resetResultList()
    setStatus('')
    hideResultContainer()
    return ;
  }
  else{
    if (_query.endsWith('~') || _query.endsWith('-') || _query.endsWith('+')){
      // Do not search string that we know are not valid query strings
      setStatus('')
      setWarning('Incomplete search query, missing terms or edit distance.')
      return;
    }
  }

  console.log("Your query is: "+ _query)

  if (!window.Worker) {
    setStatus("Cannot search: JavaScript Worker API is not supported in your browser. ");
    return ;
  }

  resetResultList()

  // posting query to worker, he's going to do the job searching in Lunr index.
  worker.postMessage({
    query: _query,
  });

  // Get result data
  httpGet("all-documents.html", function(all_documents_response) {

    worker.onmessage = function (response) {

      resetLongSearchTimerInfo()
      
      console.log("Message received from worker: ")
      console.dir(response.data)

      if (!response.data.results){
        setErrorStatus();
        throw("No data received from worker")
      }

      if (response.data.results.length == 0){
        setStatus('No results matches "' + _query + '"');
        return ;
      }

      // PARSE DATA FROM HTML DOCUMENT
      let parser = new self.DOMParser();
      let all_documents = parser.parseFromString(all_documents_response, "text/html");
      let search_results_documents = []
      
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

      if (response.data.results[0].score <= 3){
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
        else{
          setWarning('')
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
      resetLongSearchTimerInfo()
      error.preventDefault();
      setErrorStatus();
      setErrorInfos(error.message);
    }

  },
  function(error){
    console.log(error);
    resetLongSearchTimerInfo()
    setErrorStatus();
    setErrorInfos(error.message);
  });
  _setLongSearchInfosTimeout = setTimeout(setLongSearchInfos, 8000);
}

function showHideClearSearchBtn(){
  if (input.value.length>0){
    document.getElementById('search-clear-button').style.display = 'inline-block';
  }
  else{
    document.getElementById('search-clear-button').style.display = 'none';
  }
}

function launch_function(){
  try{
    showHideClearSearchBtn()
    resetLongSearchTimerInfo()

    worker.terminate()
    worker = new Worker('search-worker.js');
    
    search()
  }
  catch (err){
    console.log(err);
    setErrorStatus();
    setErrorInfos(err.message);
  }
};

input.addEventListener('input',function(event) {
  launch_function();
});
input.addEventListener("search", function(event) {
  launch_function();
});
// Close the dropdown if the use click on echap key
document.onkeydown = function(evt) {
  evt = evt || window.event;
  if (evt.key === "Escape" || evt.key === "Esc") {
      hideResultContainer()
  }
};