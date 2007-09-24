--- js/src/jsnum.c.orig	Sun Nov  5 18:37:07 2006
+++ js/src/jsnum.c	Sun Nov  5 18:42:31 2006
@@ -45,6 +45,9 @@
 #if defined(XP_WIN) || defined(XP_OS2)
 #include <float.h>
 #endif
+#if defined(__FreeBSD__)
+#include <sys/param.h>
+#endif
 #include <locale.h>
 #include <limits.h>
 #include <math.h>
@@ -532,7 +535,15 @@ static jsdouble NaN;
 
 #else
 
+#if defined(__FreeBSD__) && __FreeBSD_version >= 601000
+#include <fenv.h>
+#define FIX_FPU() (fedisableexcept(FE_ALL_EXCEPT))
+
+#else
+
 #define FIX_FPU() ((void)0)
+
+#endif /* defined(__FreeBSD__) && __FreeBSD_version >= 503000 */
 
 #endif
 
