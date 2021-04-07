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

function setPrivateInfos(message) {
  _setInfos(message, 'search-private-infos-box', 'search-private-infos');
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
      p = document.createElement('p')

  p.innerHTML = dobj.querySelector('.summary').innerHTML;
  a.setAttribute('href', dobj.querySelector('.url').innerHTML);
  a.textContent = dobj.querySelector('.fullName').innerHTML;
  
  // Adding '()' on functions and methods
  let type_value = dobj.querySelector('.type').innerHTML
  if (type_value.endsWith("Function")){
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
    li.setAttribute('class', 'private');
  }

  //Add type metadata
  let type_metadata = document.createElement('meta');
  type_metadata.setAttribute('name', 'type');
  type_metadata.setAttribute('class', 'type');
  type_metadata.setAttribute('content', type_value);
  li.appendChild(type_metadata);

  return li;
}

function setLongSearchInfos(){
  setWarning("This is taking longer than usual... You can keep waiting for the search to complete, or retry the search with other terms.");
}


function buildInfosString(search_results_documents, priv){

  let nb_classes = search_results_documents.filter(function(value){
    return (value.querySelector('.type').innerHTML.endsWith("Class") && (value.querySelector('.privacy').innerHTML.endsWith(priv ? "PRIVATE" : "VISIBLE")));
  }).length;  

  let nb_methods_or_functions = search_results_documents.filter(function(value){
    return (value.querySelector('.type').innerHTML.endsWith("Function") && (value.querySelector('.privacy').innerHTML.endsWith(priv ? "PRIVATE" : "VISIBLE")));
  }).length;  

  let nb_module_or_package = search_results_documents.filter(function(value){
    return (value.querySelector('.type').innerHTML.endsWith("Module") || value.querySelector('.kind').innerHTML.endsWith("Package")) && (value.querySelector('.privacy').innerHTML.endsWith(priv ? "PRIVATE" : "VISIBLE"));
  }).length;  

  let nb_var = search_results_documents.filter(function(value){
    return (value.querySelector('.type').innerHTML.endsWith("Attribute")) && (value.querySelector('.privacy').innerHTML.endsWith(priv ? "PRIVATE" : "VISIBLE"));

  }).length; 

  return('Including ' + nb_module_or_package + (priv ? " private" : "")
    + ' module'+(nb_module_or_package>=2? 's and' : ' or')+' package'+(nb_module_or_package>=2? 's' : '') + ', '
    + nb_classes.toString() + (priv ? " private" : "") + ' class'+(nb_classes>=2 ? 'es' : '')+', ' + nb_methods_or_functions.toString() + (priv ? " private" : "")
    + ' method'+(nb_methods_or_functions>=2? 's and' : ' or')+' function'+(nb_methods_or_functions>=2? 's' : '')+', '+' and ' + nb_var + (priv ? " private" : "") + ' variable'+(nb_var>=2? 's' : '')+'.');
}

///////////////////// FILTER //////////////////////////

// Close the dropdown if the user clicks outside of it
window.addEventListener("click", function(event) {
  let dropdown_input = document.getElementById("search-filter-dropdown-input")
  if (event && !event.target.matches('#search-filter-dropdown-input') && dropdown_input.checked == true) {
    setTimeout(function(){
      dropdown_input.checked = false;
    }, 1);
  }
});

function filterItems(types, label, dropdown_item_pressed){

  console.log("Filtering search results: " + label);

  let results_list = Array.prototype.slice.call(document.getElementById('search-results').childNodes); 
  
  var match_items = [];

  results_list.forEach(function(li, i, a){
    var match = false;
    
    types.forEach(function(type, i, a){
      if (li.querySelector('.type').getAttribute('content').endsWith(type)){
        match = true;
      }
    })

    if (match){
      li.style.display = "block";
      match_items.push(li);
    }
    else{
      li.style.display = "none";
    }
  })

  if (label.length>0){
    document.getElementById("search-filter-button").querySelector(".button-label").textContent = 'Filter: ' + label;
  }

  // Reset filter dropdown
  initFilterDropdown(results_list);
  document.getElementById("search-filter-show-all").style.display = 'block';
  document.getElementById("search-filter-button").classList.add("active")

  dropdown_item_pressed.style.display = 'none';

  console.log(match_items.length.toString() + " items matches the filter");
  console.log(match_items);

}

function showAllItems(){
  filterItems(['Class', 'Function', 'Module', 'Package', 'Attribute'], 'Choose...', document.getElementById("search-filter-show-all"))
  document.getElementById("search-filter-button").classList.remove("active")
}

function _initSearchFilter(results_list, input, types){

  let nb_things = results_list.filter(function(value){
    var match = false;
    types.forEach(function(type, i, a){

      var _type = value.querySelector('.type').getAttribute('content')
      if (!_type){
        // Filter on innerHTML if 'content' attr meta tags is undefined
        _type = value.querySelector('.type').innerHTML;
      }

      if(_type.endsWith(type)){
        match = true;
      }
    })
    return match;
  }).length;  

  if (nb_things==0){
    input.style.display = "none";
  }
  else{
    input.style.display = "block";
  }
}

function initFilterDropdown(results_list_p){

  let results_list = Array.prototype.slice.call(results_list_p);

  document.getElementById("search-filter-show-all").style.display = "none";

  _initSearchFilter(results_list, document.getElementById("search-filter-show-classes"), ["Class"])
  _initSearchFilter(results_list, document.getElementById("search-filter-show-functions"), ["Function"])
  _initSearchFilter(results_list, document.getElementById("search-filter-show-modules"), ["Module", "Package"])
  _initSearchFilter(results_list, document.getElementById("search-filter-show-attributes"), ["Attribute"])
}

///////////////////// SEARCH //////////////////////////

function search(){

  let _url = new URL(document.URL);
  console.log(_url);

  var _setLongSearchInfosTimeout = null;
  var _query = null;

  // Get the query terms
  if (!_url.searchParams.has('search-query')){
    setStatus('No search query provided.')
    return ;
  }

  _query = _url.searchParams.get('search-query');

  if (!_query.length>0){
    setStatus('No search query provided.')
    return ;
  }

  // Set the search box text to the query terms
  document.getElementById('search-box').value = _query;

  console.log("Your query is: "+ _query)

  if (!window.Worker) {
    setStatus("Cannot search: JavaScript Worker API is not supported in your browser. ");
    return ;
  }

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
      return ;
      // Error will be reported by onerror
    }

    if (response.data.results.length == 0){
      setStatus('No results matches "' + _query + '"');
      return ;
    }
    else{
      setStatus('Fetching documents...');
    }

    // Get result data
    httpGet("all-documents.html", function(response2) {
      let parser = new self.DOMParser();
      let all_documents = parser.parseFromString(response2, "text/html");
      let search_results_documents = [];
      
      response.data.results.forEach(function (result) {
          // Find the result model 
          var dobj = all_documents.getElementById(result.ref);
          
          if (!dobj){
              throw ("Cannot find document ID: " + result.ref)
          }
          // Save
          search_results_documents.push(dobj);

          // Display results: edit DOM
          let li = buildSearchResult(dobj);
          results_list.appendChild(li);

      });

      if (response.data.results[0].score <= 10){
        if (response.data.results.length > 200){
          setWarning("Your search yielded a lot of results! and there aren't many great matches. Maybe try with other terms?");
        }
        else{
          setWarning("Unfortunately, it looks like there aren't many great matches for your search. Maybe try with other terms?");
        }
      }
      else {
        if (response.data.results.length > 200){
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

        // Build complementary information string

        setInfos(buildInfosString(search_results_documents, false));
      }

      // Build PRIVATE complementary information string

      setPrivateInfos(buildInfosString(search_results_documents, true));

      initFilterDropdown(search_results_documents)

    },
    function(error){
      setErrorStatus();
      setErrorInfos(error.message);
  });

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


  _setLongSearchInfosTimeout = setTimeout(setLongSearchInfos, 8000);
}

try{
  search()
}
catch (err){
  console.log(err);
  setErrorStatus();
  setErrorInfos(err.message);
}
