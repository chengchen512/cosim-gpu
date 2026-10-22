/* SPDX-License-Identifier: Apache-2.0 */
/* Swap /en/ <-> /zh/ in the current URL. Both trees are built from the
   same Sphinx project, so the mirror page exists for every page. */
(function () {
  "use strict";
  var path = window.location.pathname;
  var match = path.match(/\/(en|zh)\//);
  if (!match) return;
  var current = match[1];
  var target = current === "en" ? "zh" : "en";
  var targetPath = path.replace("/" + current + "/", "/" + target + "/");
  var label = target === "zh" ? "中文" : "English";
  var box = document.createElement("div");
  box.className = "cosim-lang-switch";
  var link = document.createElement("a");
  link.href = targetPath;
  link.textContent = "🌐 " + label;
  link.setAttribute("hreflang", target === "zh" ? "zh-CN" : "en");
  box.appendChild(link);
  var container = document.querySelector(".wy-side-nav-search");
  if (container) {
    container.appendChild(box);
  } else {
    document.body.insertBefore(box, document.body.firstChild);
  }
})();
