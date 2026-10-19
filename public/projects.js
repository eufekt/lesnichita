// Projects are described in /projects.json.
// Are.na's public API (https://www.are.na/developers/explore) supplies images:
//   GET https://api.are.na/v3/blocks/:id
//   GET https://api.are.na/v3/channels/:slug/contents
// No token is required for public channels. Channel order follows Are.na's
// default (position_desc): the latest connection first.

(function () {
  var API = "https://api.are.na/v3";

  function h(tag, props, children) {
    var node = document.createElement(tag);
    if (props) {
      Object.keys(props).forEach(function (key) {
        var value = props[key];
        if (value == null || value === false) return;
        if (key === "text") node.textContent = value;
        else node.setAttribute(key, value);
      });
    }
    (children || []).forEach(function (child) {
      if (child) node.appendChild(child);
    });
    return node;
  }

  function fetchJson(url) {
    var controller = new AbortController();
    var timer = setTimeout(function () {
      controller.abort();
    }, 15000);
    return fetch(url, { signal: controller.signal }).then(function (res) {
      clearTimeout(timer);
      if (!res.ok) throw new Error(String(res.status));
      return res.json();
    }, function (err) {
      clearTimeout(timer);
      throw err;
    });
  }

  function loadProjects() {
    return fetchJson("/projects.json").then(function (data) {
      return Array.isArray(data) ? data : [];
    });
  }

  function blockId(value) {
    var match = String(value || "").match(/are\.na\/block\/(\d+)/);
    return match ? match[1] : null;
  }

  function channelSlug(value) {
    if (!value) return null;
    try {
      var url = new URL(value);
      if (!/(^|\.)are\.na$/.test(url.hostname)) return value;
      var parts = url.pathname.split("/").filter(Boolean);
      return parts[parts.length - 1] || null;
    } catch (e) {
      return value;
    }
  }

  function slugFromPath() {
    var parts = location.pathname.split("/").filter(Boolean);
    var index = parts.indexOf("projects");
    if (index === -1 || !parts[index + 1]) return "";
    try {
      return decodeURIComponent(parts[index + 1]);
    } catch (e) {
      return parts[index + 1];
    }
  }

  function isGif(image) {
    return image.content_type === "image/gif" || /\.gif(\?|#|$)/i.test(image.src || "");
  }

  // GIFs use the original file so they keep animating. Stills use a resized
  // Are.na version (small on the homepage, large on the project page).
  function rendition(image, size) {
    if (!image || !image.src) return null;
    var version = image[size] || image.large || image.medium || image.small;
    if (isGif(image) || !version || !version.src) {
      return { src: image.src, width: image.width, height: image.height };
    }
    var chosen = {
      src: version.src,
      width: version.width || image.width,
      height: version.height || image.height
    };
    if (version.src_2x && version.src_2x !== version.src) {
      chosen.srcset = version.src + " 1x, " + version.src_2x + " 2x";
    }
    return chosen;
  }

  function resolveMetaImage(metaImage, size) {
    if (!metaImage) return Promise.resolve(null);
    var id = blockId(metaImage);
    if (!id) return Promise.resolve({ src: metaImage });
    return fetchJson(API + "/blocks/" + encodeURIComponent(id)).then(function (block) {
      return rendition(block.image, size);
    });
  }

  function applyImage(img, chosen) {
    img.src = chosen.src;
    img.alt = chosen.alt || "";
    if (chosen.width) img.setAttribute("width", String(chosen.width));
    if (chosen.height) img.setAttribute("height", String(chosen.height));
    if (chosen.srcset) img.setAttribute("srcset", chosen.srcset);
    img.decoding = "async";
  }

  function renderHome(section, projects) {
    var list = h("ul");
    projects.forEach(function (project) {
      if (!project || !project.slug || !project.title) return;
      var href = "/projects/" + encodeURIComponent(project.slug) + "/";
      var line = h("p", { class: "project-line" });
      line.appendChild(h("a", { href: href, text: project.title }));
      if (project.date) {
        line.appendChild(h("span", { class: "subtitle", text: String(project.date) }));
      }
      var item = h("li", null, [line]);
      if (project.description) {
        item.appendChild(h("p", { class: "project-description", text: project.description }));
      }
      if (project.tags && project.tags.length) {
        item.appendChild(h("p", { class: "project-tags", text: project.tags.join(", ") }));
      }
      list.appendChild(item);

      resolveMetaImage(project.meta_image, "small").then(function (chosen) {
        if (!chosen) return;
        var img = h("img", { class: "project-thumb", alt: "" });
        chosen.alt = "";
        applyImage(img, chosen);
        var thumb = h("a", {
          class: "image-link",
          href: href,
          "aria-label": project.title
        }, [img]);
        item.insertBefore(thumb, line);
      }).catch(function () {});
    });
    section.appendChild(list);
  }

  function imageItem(block, chosen) {
    var img = h("img");
    chosen.alt = (block.image && block.image.alt_text) || block.title || "";
    applyImage(img, chosen);
    img.loading = "lazy";
    var link = h("a", {
      class: "image-link",
      href: "https://www.are.na/block/" + block.id
    }, [img]);
    return h("li", null, [link]);
  }

  function fetchChannel(slug, onPage) {
    function pageAt(n) {
      var url = API + "/channels/" + encodeURIComponent(slug) +
        "/contents?per=100&sort=position_desc&page=" + n;
      return fetchJson(url).then(function (body) {
        onPage(body.data || []);
        if (body.meta && body.meta.has_more_pages) {
          var next = body.meta.next_page || (n + 1);
          return new Promise(function (resolve) {
            setTimeout(resolve, 300);
          }).then(function () {
            return pageAt(next);
          });
        }
      });
    }
    return pageAt(1);
  }

  function renderProject(root, project) {
    root.textContent = "";
    if (!project) {
      root.appendChild(h("p", { text: "This project is not listed." }));
      return;
    }

    document.title = project.title + " — Nichita Hariton";
    var description = document.querySelector('meta[name="description"]');
    if (description && project.description) {
      description.setAttribute("content", project.description);
    }

    root.appendChild(h("h1", { text: project.title }));
    if (project.date) {
      root.appendChild(h("p", { class: "project-date", text: String(project.date) }));
    }
    if (project.description) {
      root.appendChild(h("p", { class: "project-description", text: project.description }));
    }
    if (project.tags && project.tags.length) {
      root.appendChild(h("p", { class: "project-tags", text: project.tags.join(", ") }));
    }

    var metaSlot = null;
    if (project.meta_image) {
      metaSlot = h("div", { class: "meta-slot" });
      root.appendChild(metaSlot);
      resolveMetaImage(project.meta_image, "large").then(function (chosen) {
        if (!chosen) {
          metaSlot.remove();
          return;
        }
        var metaId = blockId(project.meta_image);
        var meta = h("a", {
          class: "image-link",
          href: metaId ? "https://www.are.na/block/" + metaId : project.meta_image
        });
        var img = h("img", { class: "meta-image" });
        chosen.alt = project.title;
        applyImage(img, chosen);
        meta.appendChild(img);
        metaSlot.appendChild(meta);
      }).catch(function () {
        metaSlot.remove();
      });
    }

    if (project.arena_channel) {
      root.appendChild(h("p", null, [
        h("a", { href: project.arena_channel, text: "are.na" })
      ]));
    }

    var slug = channelSlug(project.arena_channel);
    if (!slug) return;

    var status = h("p", { class: "project-status", text: "loading" });
    var images = h("ul", { class: "images", "aria-label": "Channel images" });
    root.appendChild(status);
    root.appendChild(images);

    var count = 0;
    fetchChannel(slug, function (blocks) {
      blocks.forEach(function (block) {
        if (!block || block.state === "failed" || !block.image) return;
        var chosen = rendition(block.image, "large");
        if (!chosen) return;
        images.appendChild(imageItem(block, chosen));
        count += 1;
      });
      if (count > 0 && status.parentNode) status.remove();
    }).then(function () {
      if (count === 0) status.textContent = "This channel has no images.";
    }).catch(function () {
      if (count > 0) {
        images.appendChild(h("li", null, [
          h("p", { text: "Some later images in this channel could not be loaded." })
        ]));
        return;
      }
      status.textContent = "";
      status.appendChild(document.createTextNode("The channel images could not be loaded. "));
      status.appendChild(h("a", { href: project.arena_channel, text: "are.na" }));
    });
  }

  function start() {
    var section = document.querySelector("[data-projects]");
    var page = document.querySelector("[data-project-page]");
    if (!section && !page) return;

    loadProjects().then(function (projects) {
      if (section) renderHome(section, projects);
      if (!page) return;
      var slug = slugFromPath();
      var project = null;
      for (var i = 0; i < projects.length; i += 1) {
        if (projects[i].slug === slug) {
          project = projects[i];
          break;
        }
      }
      renderProject(page, project);
    }).catch(function () {
      if (section) {
        section.appendChild(h("p", { text: "Projects could not be loaded." }));
      }
      if (page) {
        page.textContent = "";
        page.appendChild(h("p", { text: "This project could not be loaded." }));
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
