// This file contains the code that drives the search system.
// It's included in every HTML file.
// Ideas for improvments: 
// - Include filtering buttons:
//    - search only in the current module
//    - search only for specific types / kind

//////// GLOBAL VARS /////////

var input = document.getElementById('search-box');
var results_container = document.getElementById('search-results-container');
let results_list = document.getElementById('search-results'); 

// Setup the search worker variable
var worker = undefined;

// setTimeout variable to warn when a search takes too long
var _setLongSearchInfosTimeout = null;

//////// FUNCTIONS /////////

function _setInfos(message, box_id, text_id) {
  document.getElementById(text_id).textContent = message;
  if (message.length>0){
    document.getElementById(box_id).style.display = 'block';
  }
  else{
    document.getElementById(box_id).style.display = 'none';
  }
}

/**
 * Set the search status.
 */
function setStatus(message) {
  document.getElementById('search-status').textContent = message;
}

/**
 * Show a warning, hide warning box if empty string.
 */
function setWarning(message) {
  _setInfos(message, 'search-warn-box', 'search-warn');
}

function setErrorStatus() {
  resetLongSearchTimerInfo()
  setStatus("Something went wrong.");
  setErrorInfos();
}

function setErrorInfos(message) {
  if (message != undefined){
    setWarning(message);
  }
  else{
    setWarning("Error: See development console for details.");
  }
}

function resetLongSearchTimerInfo(){
  if (_setLongSearchInfosTimeout){
    clearTimeout(_setLongSearchInfosTimeout);
  }
}

/**
 * Transform list item as in all-documents.html into a search result row.
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

function setLongSearchInfos(){
  setWarning("This is taking longer than usual... You can keep waiting for the search to complete, or retry the search with other terms.");
}

function hideResultContainer(){
  results_container.style.display = 'none';
  if (!document.body.classList.contains("search-help-hidden")){
    document.body.classList.add("search-help-hidden");
  }
}

function showResultContainer(){
  results_container.style.display = 'block';
}

function toggleSearchHelpText() {
  document.body.classList.toggle("search-help-hidden");
  if (document.body.classList.contains("search-help-hidden") && input.value.length==0){
    hideResultContainer();
  }
  else{
    showResultContainer();
  }
}

function resetResultList(){
  results_list.innerHTML = '';
}

function clearSearch(){
  hideResultContainer();
  resetResultList();
  setWarning('');
  setStatus('');

  input.value = '';
  updateClearSearchBtn();
}

// This gives the UI the opportunity to refresh while we're iterating over a large list.
function asyncFor(iters, callback) { // -> Promise of List of results returned by callback
  const promise_global = new Promise((resolve_global, _reject) => {
    let promises = [];
    iters.forEach((element) => {
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

/** 
 * Do the actual searching business
 */
function search(){

  setWarning('');
  showResultContainer();
  setStatus("Searching...");

  // Get the query terms 

  let _query = input.value;

  if (!_query.length>0){
    resetResultList();
    setStatus('');
    hideResultContainer();
    return;
  }

  console.log("Your query is: "+ _query)

  if (!window.Worker) {
    setStatus("Cannot search: JavaScript Worker API is not supported in your browser. ");
    return;
  }

  resetResultList();

  // posting query to worker, he's going to do the job searching in Lunr index.
  worker.postMessage({
    query: _query,
  });

  // Get result data
  httpGet("all-documents.html", function(all_documents_response) {
    
    // Save a worker reference here to check if the worker has been
    // re-created or not, if it has been re-created, it means that the search
    // results should be discarded.
    let _search_worker = worker

    _search_worker.onmessage = function (response) {
      resetLongSearchTimerInfo();

      console.log("Message received from worker: ");
      console.dir(response.data);

      if (!response.data.results){
        setErrorStatus();
        throw("No data received from worker");
      }

      if (response.data.results.length == 0){
        setStatus('No results matches "' + _query + '"');
        return;
      }

      setStatus("One sec...");

      // Parse data from HTML document, 
      // this can take some time, so we wrap it in a setTimeout()
      setTimeout(() => {
        let parser = new self.DOMParser();
        let all_documents = parser.parseFromString(all_documents_response, "text/html");
        
        // Look for results data in parsed all-documents.html
        asyncFor(response.data.results, (result) => {

            // Find the result model and display result row.
            var dobj = all_documents.getElementById(result.ref);
            
            if (!dobj){
                setErrorStatus();
                throw ("Cannot find document ID: " + result.ref);
            }

            // Return result data
            return dobj;

        }).then((results) => {
          // Check if this search results should be displayed or not
          if (!(worker === _search_worker)){
            // Do not display results for a search that is not the last one
            return;
          }

          // Edit DOM
          resetResultList();
          results.forEach((dobj) => {
            results_list.appendChild(buildSearchResult(dobj));
          });

          if (response.data.results[0].score <= 5){
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
              setWarning('');
            }
          }

          let public_search_results = results.filter(function(value){
            return !value.querySelector('.privacy').innerHTML.includes("PRIVATE");
          })

          if (public_search_results.length==0){
            setStatus('No results matches "' + _query + '". Some private objects matches your search though.');
          }
          else{
            setStatus(
              'Search for "' + _query + '" yielded ' + public_search_results.length + ' ' +
              (public_search_results.length === 1 ? 'result' : 'results') + '.');
          }

          // End
        
        }).catch((err) => {
          setErrorStatus();
          throw err;
        }); // Results promise resolved

      }, 0); // setTimeout block

    }; // Worker on message block, most likely an error in query parsing.
    _search_worker.onerror = function(error) {
      console.log(error);
      setErrorStatus();
      setErrorInfos(error.message);
    };

  }, // On httpGet all-documents.html block

  function(error){ // On error: httpGet all-documents.html
    setErrorStatus();
  });

  // After five seconds of searching, warn that this is taking more time than usual.
  _setLongSearchInfosTimeout = setTimeout(setLongSearchInfos, 5000);

} // end search() function

/**
 * Show and hide the (X) button depending on the current search input.
 * We do not show the (X) button when there is no search going on.
 */
function updateClearSearchBtn(){
  
  if (input.value.length>0){
    document.getElementById('search-clear-button').style.display = 'inline-block';
  }
  else{
    document.getElementById('search-clear-button').style.display = 'none';
  }
}

/** 
 * Main entrypoint to [re]launch the search.
 * Called everytime the search bar is edited.
*/
function launch_search(){

  // creating new Worker could be UI blocking, 
  // we give the UI the opportunity to refresh here
  setTimeout(() => {
    updateClearSearchBtn();
    resetLongSearchTimerInfo();

    // We don't want to run concurrent searches.
    // Kill and re-create worker.
    if (worker!=undefined){
      worker.terminate();
    }
    worker = new Worker('search-worker.js');
    search();
  }, 0);
}


////// SETUP //////

// Attach launch_search() to search text field update events.
input.addEventListener('input',function(event) {
  launch_search();
});
input.addEventListener("keyup", function(event) {
  if (event.key === 'Enter') {
    launch_search();
  }
});

// Close the dropdown if the user clicks on echap key
document.onkeydown = function(evt) {
  evt = evt || window.event;
  if (evt.key === "Escape" || evt.key === "Esc") {
      hideResultContainer();
  }
};

// Init search and help text. 
// search box is not visible by default because
// we don't want to show it if the browser do not support JS.
window.addEventListener('load', (event) => {
  document.getElementById('search-box-container').style.display = 'block';
  document.getElementById('search-help-box').style.display = 'block';
  hideResultContainer();
});

// Hide the dropdown if the user clicks outside of it
window.addEventListener("click", function(event) {
  if (event){
      if (!event.target.closest('#search-results-container') 
          && !event.target.closest('#search-box')
          && !event.target.closest('#search-help-button')){
            hideResultContainer();
            return;
      }
      if (event.target.closest('#search-box')){
        if (input.value.length>0){
          showResultContainer();
        }
      }
  }
});