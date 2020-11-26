.. Configuration adjusted from https://setupdocx.sourceforge.io/configurations/epydoc/epydoc_sphinx_iframe/index.html

ReST Quick Ref
^^^^^^^^^^^^^^

.. raw:: html

   <style>

      div[aria-label^=breadcrumbs], footer, h1 {
         display: none;
      }

      div.wy-nav-content {
          padding: 0px 0px 0px 0px;
          max-width: 100%;
      }
      div.pydoctor-sphinx {
          position: relative;
      }
      iframe.pydoctor-sphinx  {
          position: absolute;
          top: 0;
          width: 100%;
          border: none;
      }
   </style>

   <script>
      document.body.onload = function(o){
          document.getElementById("glu").style.height = document.body.scrollHeight+"px";
      }
      document.body.onresize = function(o){
         document.getElementById("glu").style.height = document.body.scrollHeight+"px";
      }
   </script>  
   
   <div class="pydoctor-sphinx">
      <iframe id='glu'
         class="pydoctor-sphinx"
         src="rst/rst.html"
         seamless
      ></iframe>
   </div>
