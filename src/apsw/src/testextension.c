/* This code is to test extension loading and is taken from
   https://sqlite.org/cvstrac/wiki/wiki?p=LoadableExtensions */


    #include <sqlite3ext.h>
    SQLITE_EXTENSION_INIT1

    /*
    ** The half() SQL function returns half of its input value.
    */
    static void halfFunc(
      sqlite3_context *context,
      int argc,
      sqlite3_value **argv
    ){
      sqlite3_result_double(context, 0.5*sqlite3_value_double(argv[0]));
    }

    /* SQLite invokes this routine once when it loads the extension.
    ** Create new functions, collating sequences, and virtual table
    ** modules here.  This is usually the only exported symbol in
    ** the shared library.
    */
    int sqlite3_extension_init(
      sqlite3 *db,
      char **pzErrMsg,
      const sqlite3_api_routines *pApi
    ){
      SQLITE_EXTENSION_INIT2(pApi)
      sqlite3_create_function(db, "half", 1, SQLITE_ANY, 0, halfFunc, 0, 0);
      return 0;
    }


/* this is code added by me and checks that alternate entry points work by
   providing an double function */

    static void doubleFunc(
      sqlite3_context *context,
      int argc,
      sqlite3_value **argv
    ){
      sqlite3_result_double(context, 2.0*sqlite3_value_double(argv[0]));
    }

    int alternate_sqlite3_extension_init(
      sqlite3 *db,
      char **pzErrMsg,
      const sqlite3_api_routines *pApi
    ){
      SQLITE_EXTENSION_INIT2(pApi)
      sqlite3_create_function(db, "doubleup", 1, SQLITE_ANY, 0, doubleFunc, 0, 0);
      return 0;
    }
