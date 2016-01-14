# Registers the JSX language in Komodo.

import logging
from koUDLLanguageBase import KoUDLLanguage

log = logging.getLogger("koJSXLanguage")
#log.setLevel(logging.DEBUG)

def registerLanguage(registry):
    log.debug("Registering language JSX")
    registry.registerLanguage(KoJSXLanguage())

class KoJSXLanguage(KoUDLLanguage):

    # ------------ Komodo Registration Information ------------ #

    name = "JSX"
    lexresLangName = "JSX"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" % name
    _reg_categories_ = [("komodo-language", name)]
    _reg_clsid_ = "e5611d6c-c2b8-4fd7-b1f8-9138f8d70076"

    primary = 0  # Whether the language shows up in Komodo's first level language menus.

    # ------------ Sub-language Controls ------------ #
    lang_from_udl_family = {
        'M': 'HTML',
        'CSS': 'CSS',
        'CSL': 'JavaScript'
    }

    sample = """// tutorial10.js
var CommentList = React.createClass({
  render: function() {
    var commentNodes = this.props.data.map(function(comment) {
      return (
        <Comment author={comment.author} key={comment.id}>
          {comment.text}
        </Comment>
      );
    });
    return (
      <div className="commentList">
        {commentNodes}
      </div>
    );
  }
});"""