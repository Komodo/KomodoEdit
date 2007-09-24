--- config/rules.mk.orig	Thu Sep 14 14:07:03 2006
+++ config/rules.mk	Wed Oct 18 11:00:09 2006
@@ -442,9 +442,7 @@
 endif
 
 ifeq ($(OS_ARCH),FreeBSD)
-ifdef IS_COMPONENT
-EXTRA_DSO_LDOPTS += -Wl,-Bsymbolic
-endif
+EXTRA_DSO_LDOPTS += -Wl,-Bsymbolic -lc
 endif
 
 ifeq ($(OS_ARCH),NetBSD)
