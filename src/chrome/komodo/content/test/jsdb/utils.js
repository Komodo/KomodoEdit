/* -*- indent-tabs-mode: nil -*-  */

// Misc. useful mozilla/javascript utils


var log = ko.logging.getLogger("jsd_utils");
log.setLevel(ko.logging.LOG_DEBUG);
log.debug("jsd_utils loading...");


function find_class(name) {
    return Components.classes[name];
}

function find_interface(name) {
    return Components.interfaces[name];
}

function create_instance(class_name, interface_name) {
    var iface = find_interface(interface_name);
    return find_class(class_name).createInstance (iface);
}

function get_service(class_name, interface_name) {
    var iface = find_interface(interface_name);
    return find_class(class_name).getService(iface);
}

function keys(h) {
    var a = [];
    for (k in h) {
        a.push(k);
    }
    return a;
}
