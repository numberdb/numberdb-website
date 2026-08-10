window.MathJax = {
  tex: {
    inlineMath: [['$', '$'], ['\\(', '\\)']]
  },
  svg: {
    fontCache: 'global',
  }
};

//MathJax is served from this site, not from jsDelivr. Every page loads it, so
//the CDN version meant every visitor announced themselves to a third party
//before a single formula appeared -- and it made the site's formulas depend on
//someone else staying up.
//
//The path is written out rather than built by {% static %} because this is a
//static file, not a template. It matches STATIC_URL, which is '/static/'.
(function () {
  var script = document.createElement('script');
  script.src = '/static/vendor/mathjax/tex-svg.js';
  script.async = true;
  document.head.appendChild(script);
})();
