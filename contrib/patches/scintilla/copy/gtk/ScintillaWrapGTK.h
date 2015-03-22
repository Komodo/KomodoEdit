#ifndef SCINTILLAWRAPGTK_H
#define SCINTILLAWRAPGTK_H

bool ScintillaWrapGTK_gtk_widget_get_realized(GtkWidget *widget);
void ScintillaWrapGTK_gtk_widget_set_realized(GtkWidget *widget, bool isRealized);
bool ScintillaWrapGTK_gtk_widget_get_mapped(GtkWidget *widget);
void ScintillaWrapGTK_gtk_widget_set_mapped(GtkWidget *widget, bool on);
bool ScintillaWrapGTK_gtk_widget_get_visible(GtkWidget *widget);
void ScintillaWrapGTK_gtk_widget_set_sensitive(GtkWidget *widget, bool on);
void ScintillaWrapGTK_gtk_widget_set_allocation(GtkWidget *widget, GtkAllocation *allocation);
bool ScintillaWrapGTK_gtk_widget_has_focus(void *widget);
void ScintillaWrapGTK_gtk_widget_set_can_focus(GtkWidget *widget, bool on);
cairo_surface_t *ScintillaWrapGTK_gdk_window_create_similar_surface(GdkWindow *window, cairo_content_t content, int width, int height);

#endif
