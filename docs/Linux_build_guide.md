## Linux build guide for Komodo Edit 12


### STEP 1 Install dependencies

#### DEPENDENCIES
- gcc
- git
- zip
- unzip
- subversion
- libgtk-2-dev
- libdbus-glib-1-dev
- yasm
- libasound2-dev
- libpulse-dev
- libxt-dev

<br />

Debian
```
sudo apt install git zip unzip subversion autoconf2.13 \
	libgtk2.0-dev libdbus-glib-1-dev yasm libasound2-dev \
	libpulse-dev libxt-dev
```
<br />


#### SPECIAL DEPENDENCIES
- autoconf2.13 `There should be a package for this on most distros.`
- perl-5.22.4     `I recommend using perlbrew.`
- g++-4.9   `You have to find this on your own.`


<br />
<br />

### STEP 2 Download repo and configure Mozilla

```
git clone https://github.com/Komodo/KomodoEdit.git --branch master --single-branch --depth 1
cd KomodoEdit/mozilla
python build.py configure --gcc gcc --gxx g++-4.9 -k 12.10
```
<br />


### STEP 3 Build Mozilla

`python build.py all   # Build`

or

`python build.py distclean all`
To delete and re-download Mozilla again

<br />

#### Build Errors
Since Komodo uses a version of Mozilla from 2014 you should expect errors.

<br />
<br />


Error`mozalloc.h:206:33: error: ‘bad_alloc’ in namespace ‘std’ does not name a type`

make sure you're using g++4.9

<br />
<br />

Error `exception_handler.h:192:21: error: field ‘context’ has incomplete type ‘google_breakpad::ucontext’`

 
```
# fix
./build/moz3500-ko12.10/mozilla/toolkit/crashreporter/google-breakpad/src/client/linux/handler/exception_handler.h
@@ -189,7 +189,7 @@ class ExceptionHandler {
   struct CrashContext {
     siginfo_t siginfo;
     pid_t tid;  // the crashing thread.
-    struct ucontext context;
+    struct ucontext_t context;
 #if !defined(__ARM_EABI__)
     // #ifdef this out because FP state is not part of user ABI for Linux ARM.
     struct _libc_fpstate float_state;
```
<br />
<br />


Error `nsLocalFileUnix.cpp:1397:46: error: ‘minor’ was not declared in this scope`
```
# fix
./build/moz3500-ko12.10/mozilla/xpcom/io/nsLocalFileUnix.cpp
@@ -13,6 +13,7 @@
 #include <sys/types.h>
 #include <sys/stat.h>
+#include <sys/sysmacros.h>
 #include <unistd.h>
 #include <fcntl.h>
 #include <errno.h>


./build/moz3500-ko12.10/mozilla/config/system-headers
@@ -1073,6 +1073,7 @@
 sys/syscall.h
 sys/sysctl.h
 sys/sysinfo.h
+sys/sysmacros.h
 sys/sysmp.h
 sys/syssgi.h
 sys/system_properties.h
```
clear cache to avoid binutils error `run python build.py clean`
<br />
<br />



Error `minidump_writer.cc:276:56: error: ‘ucontext’ does not name a type`
```
# fix
./build/moz3500-ko12.10/mozilla/toolkit/crashreporter/google-breakpad/src/client/linux/minidump_writer/minidump_writer.cc
@@ -173,7 +173,7 @@ void CPUFillFromThreadInfo(MDRawContextX86 *out,
 // Juggle an x86 ucontext into minidump format
 //   out: the minidump structure
 //   info: the collection of register structures.
-void CPUFillFromUContext(MDRawContextX86 *out, const ucontext *uc,
+void CPUFillFromUContext(MDRawContextX86 *out, const ucontext_t *uc,
                          const struct _libc_fpstate* fp) {
   const greg_t* regs = uc->uc_mcontext.gregs;
 
@@ -273,7 +273,7 @@ void CPUFillFromThreadInfo(MDRawContextAMD64 *out,
   my_memcpy(&out->flt_save.xmm_registers, &info.fpregs.xmm_space, 16 * 16);
 }
 
-void CPUFillFromUContext(MDRawContextAMD64 *out, const ucontext *uc,
+void CPUFillFromUContext(MDRawContextAMD64 *out, const ucontext_t *uc,
                          const struct _libc_fpstate* fpregs) {
   const greg_t* regs = uc->uc_mcontext.gregs;
 
@@ -340,7 +340,7 @@ void CPUFillFromThreadInfo(MDRawContextARM* out,
 #endif
 }
 
-void CPUFillFromUContext(MDRawContextARM* out, const ucontext* uc,
+void CPUFillFromUContext(MDRawContextARM* out, const ucontext_t* uc,
                          const struct _libc_fpstate* fpregs) {
   out->context_flags = MD_CONTEXT_ARM_FULL;
 
@@ -1479,7 +1479,7 @@ class MinidumpWriter {
   const int fd_;  // File descriptor where the minidum should be written.
   const char* path_;  // Path to the file where the minidum should be written.
 
-  const struct ucontext* const ucontext_;  // also from the signal handler
+  const struct ucontext_t* const ucontext_;  // also from the signal handler
   const struct _libc_fpstate* const float_state_;  // ditto
   LinuxDumper* dumper_;
   MinidumpFileWriter minidump_writer_;
```


<br />
<br />


Error`exception_handler.cc error: field ‘context’ has incomplete type ‘google_breakpad::ucontext’`
```
# fix
./build/moz3500-ko12.10/mozilla/toolkit/crashreporter/google-breakpad/src/client/linux/handler/exception_handler.cc
@@ -393,10 +393,10 @@ bool ExceptionHandler::HandleSignal(int sig, siginfo_t* info, void* uc) {
   }
   CrashContext context;
   memcpy(&context.siginfo, info, sizeof(siginfo_t));
-  memcpy(&context.context, uc, sizeof(struct ucontext_t));
+  memcpy(&context.context, uc, sizeof(struct ucontext));
 #if !defined(__ARM_EABI__)
   // FP state is not part of user ABI on ARM Linux.
-  struct ucontext_t *uc_ptr = (struct ucontext_t*)uc;
+  struct ucontext *uc_ptr = (struct ucontext*)uc;
   if (uc_ptr->uc_mcontext.fpregs) {
     memcpy(&context.float_state,
            uc_ptr->uc_mcontext.fpregs,
@@ -420,7 +420,7 @@ bool ExceptionHandler::SimulateSignalDelivery(int sig) {
   // ExceptionHandler::HandleSignal().
   siginfo.si_code = SI_USER;
   siginfo.si_pid = getpid();
-  struct ucontext_t context;
+  struct ucontext context;
   getcontext(&context);
   return HandleSignal(sig, &siginfo, &context);
 }
```

<br />
<br />
<br />


### STEP 4 Build Komodo

make sure your using perl-5.22.4 
`perl --version`

```
cd .. # go back to main repo directory
export PATH=`pwd`/util/black:$PATH   # Komodo's "bk" build tool
git submodule update --init
git submodule update --remote
bk configure -V 12.10.0-devel
bk build
```

#### run it!
`bk run`

or

`./util/black/bk.py run`






