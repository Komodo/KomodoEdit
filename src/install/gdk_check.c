#include <gtk/gtk.h>

int main() {
  return gtk_check_version(2, 24, 0) == NULL ? 0 : 1;
}
