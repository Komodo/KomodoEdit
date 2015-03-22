/**
 * GTK library wrapper - to support a custom version of GTK.
 *
 * Use these defines to choose a lower version of GTK to link against:
 *   KOMODO_USE_GTK_MAJOR - the major version number to support
 *   KOMODO_USE_GTK_MINOR - the minor version number to support
 */

#include <gtk/gtk.h>
#include "ScintillaWrapGTK.h"

bool ScintillaWrapGTK_gtk_widget_get_realized(GtkWidget *widget) {
#if GTK_CHECK_VERSION(2,20,0) && GTK_CHECK_VERSION(KOMODO_USE_GTK_MAJOR, KOMODO_USE_GTK_MINOR, 0)
    return gtk_widget_get_realized(GTK_WIDGET(widget));
#else
    return GTK_WIDGET_REALIZED(widget);
#endif
}

void ScintillaWrapGTK_gtk_widget_set_realized(GtkWidget *widget, bool on) {
#if GTK_CHECK_VERSION(2,20,0) && GTK_CHECK_VERSION(KOMODO_USE_GTK_MAJOR, KOMODO_USE_GTK_MINOR, 0)
    gtk_widget_set_realized(widget, on ? TRUE : FALSE);
#else
    if (on) {
        GTK_WIDGET_SET_FLAGS(widget, GTK_REALIZED);
    } else {
        GTK_WIDGET_UNSET_FLAGS(widget, GTK_REALIZED);
    }
#endif
}


bool ScintillaWrapGTK_gtk_widget_get_mapped(GtkWidget *widget) {
#if GTK_CHECK_VERSION(2,20,0) && GTK_CHECK_VERSION(KOMODO_USE_GTK_MAJOR, KOMODO_USE_GTK_MINOR, 0)
    return gtk_widget_get_mapped(GTK_WIDGET(widget));
#else
    return GTK_WIDGET_MAPPED(widget);
#endif
}

void ScintillaWrapGTK_gtk_widget_set_mapped(GtkWidget *widget, bool on) {
#if GTK_CHECK_VERSION(2,20,0) && GTK_CHECK_VERSION(KOMODO_USE_GTK_MAJOR, KOMODO_USE_GTK_MINOR, 0)
    gtk_widget_set_mapped(widget, on ? TRUE : FALSE);
#else
    if (on) {
        GTK_WIDGET_SET_FLAGS(widget, GTK_MAPPED);
    } else {
        GTK_WIDGET_UNSET_FLAGS(widget, GTK_MAPPED);
    }
#endif
}


bool ScintillaWrapGTK_gtk_widget_get_visible(GtkWidget *widget) {
#if GTK_CHECK_VERSION(2,20,0) && GTK_CHECK_VERSION(KOMODO_USE_GTK_MAJOR, KOMODO_USE_GTK_MINOR, 0)
    return gtk_widget_get_visible(GTK_WIDGET(widget));
#else
    return GTK_WIDGET_VISIBLE(widget);
#endif
}


bool ScintillaWrapGTK_gtk_widget_has_focus(void *widget) {
#if GTK_CHECK_VERSION(2,20,0) && GTK_CHECK_VERSION(KOMODO_USE_GTK_MAJOR, KOMODO_USE_GTK_MINOR, 0)
    return gtk_widget_has_focus(GTK_WIDGET(widget));
#else
    return GTK_WIDGET_HAS_FOCUS(widget);
#endif
}

void ScintillaWrapGTK_gtk_widget_set_can_focus(GtkWidget *widget, bool on) {
#if GTK_CHECK_VERSION(2,20,0) && GTK_CHECK_VERSION(KOMODO_USE_GTK_MAJOR, KOMODO_USE_GTK_MINOR, 0)
    gtk_widget_set_can_focus(widget, on ? TRUE : FALSE);
#else
    if (on) {
        GTK_WIDGET_SET_FLAGS(widget, GTK_CAN_FOCUS);
    } else {
        GTK_WIDGET_UNSET_FLAGS(widget, GTK_CAN_FOCUS);
    }
#endif
}


void ScintillaWrapGTK_gtk_widget_set_allocation(GtkWidget *widget, GtkAllocation *allocation) {
#if GTK_CHECK_VERSION(2,20,0) && GTK_CHECK_VERSION(KOMODO_USE_GTK_MAJOR, KOMODO_USE_GTK_MINOR, 0)
    gtk_widget_set_allocation(widget, allocation);
#else
    widget->allocation = *allocation;
#endif
}


void ScintillaWrapGTK_gtk_widget_set_sensitive(GtkWidget *widget, bool on) {
#if GTK_CHECK_VERSION(2,20,0) && GTK_CHECK_VERSION(KOMODO_USE_GTK_MAJOR, KOMODO_USE_GTK_MINOR, 0)
    gtk_widget_set_sensitive(widget, on ? TRUE : FALSE);
#else
    if (on) {
        GTK_WIDGET_SET_FLAGS(widget, GTK_SENSITIVE);
    } else {
        GTK_WIDGET_UNSET_FLAGS(widget, GTK_SENSITIVE);
    }
#endif
}


cairo_surface_t *ScintillaWrapGTK_gdk_window_create_similar_surface(GdkWindow *window, cairo_content_t content, int width, int height) {
#if GTK_CHECK_VERSION(2,22,0) && GTK_CHECK_VERSION(KOMODO_USE_GTK_MAJOR, KOMODO_USE_GTK_MINOR, 0)
	return gdk_window_create_similar_surface(window, content, width, height);
#else
	cairo_surface_t *window_surface, *surface;
	g_return_val_if_fail(GDK_IS_WINDOW(window), NULL);
	window_surface = GDK_DRAWABLE_GET_CLASS(window)->ref_cairo_surface(window);
	surface = cairo_surface_create_similar(window_surface, content, width, height);
	cairo_surface_destroy(window_surface);
	return surface;
#endif
}
