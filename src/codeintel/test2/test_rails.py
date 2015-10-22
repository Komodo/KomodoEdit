#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
# 
# The contents of this file are subject to the Mozilla Public License
# Version 1.1 (the "License"); you may not use this file except in
# compliance with the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
# 
# Software distributed under the License is distributed on an "AS IS"
# basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
# License for the specific language governing rights and limitations
# under the License.
# 
# The Original Code is Komodo code.
# 
# The Initial Developer of the Original Code is ActiveState Software Inc.
# Portions created by ActiveState Software Inc are Copyright (C) 2000-2007
# ActiveState Software Inc. All Rights Reserved.
# 
# Contributor(s):
#   ActiveState Software Inc
# 
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
# 
# ***** END LICENSE BLOCK *****

"""Test Rails-specific codeintel handling."""

import os
import sys
import random
import re
import time
from os.path import join, dirname, abspath, exists, basename
from glob import glob
import unittest
import subprocess
import logging

from codeintel2.environment import SimplePrefsEnvironment
from codeintel2.util import indent, dedent, banner, markup_text, unmark_text

from testlib import TestError, TestSkipped, TestFailed, tag
from citestsupport import CodeIntelTestCase, writefile



log = logging.getLogger("test")


def _splitall(path):
    r""" Copied from mkrc.py, which copies it from Python Cookbook
    """
    allparts = []
    import os.path
    while 1:
        parts = os.path.split(path)
        if parts[0] == path:  # sentinel for absolute paths
            allparts.insert(0, parts[0])
            break
        elif parts[1] == path: # sentinel for relative paths
            allparts.insert(0, parts[1])
            break
        else:
            path = parts[0]
            allparts.insert(0, parts[1])
    allparts = [p for p in allparts if p] # drop empty strings 
    return allparts


class _BaseTestCase(CodeIntelTestCase):
    """Base class for test cases to run for both pure-Ruby and
    Ruby-in-multilang. Sub-class must implement the following:

        lang = <lang>
        ext = <ext>
    """
    test_dir = join(os.getcwd(), "tmp")

class PureRailsTestCase(_BaseTestCase):
    lang = "Ruby"
    ext = ".rb"
    heredoc_support = True
    env = SimplePrefsEnvironment(codeintel_selected_catalogs=['rails'])
    
    def test_catalog(self):
        catalogs_zone = self.mgr.db.get_catalogs_zone()
        for catalog_info in catalogs_zone.avail_catalogs(["rails"]):
            if catalog_info['selected']:
                rails_info = catalog_info
                break
        else:
            self.fail("rails not found in the available catalogs")

        self.failUnlessEqual(rails_info["name"], "Rails")
        self.failUnless(rails_info["description"] is not None)

    def test_railsenv_model_basic(self):
        test_dir = join(self.test_dir, "railsapp01", "app", "models")
        main_filename = "cart1.rb"
        main_content, main_positions = \
          unmark_text(self.adjust_content(dedent("""\
            class Cart < ActiveRecord::<1>Base
                Cart.<2>acts_as_list
                def octopus
                    self.<3>insert_at(0)
                    i = 4
                    print "you owe #{i.<4>gigabyte} dollars"
                end
            end
        """)))
        main_path = join(test_dir, main_filename)
        writefile(main_path, main_content)
        main_buf = self.mgr.buf_from_path(main_path)
        targets = [[("class", "Base"),],
             [("function", "acts_as_list"),],
             [("function", "insert_at"),],
             [("function", "megabyte"),],
             ]
        for i in range(len(targets)):
            self.assertCompletionsInclude2(main_buf, main_positions[i + 1],
                                           targets[i])
            ## Verify we don't get false hits
            self.assertCompletionsDoNotInclude(markup_text(main_content,
                                                           pos=main_positions[i + 1]),
                                               targets[i])

    @tag("global")
    def test_railsenv_model_toplevel_1(self):
        test_dir = join(self.test_dir, "railsapp01", "app", "models")
        main_filename = "cart1.rb"
        main_content, main_positions = \
          unmark_text(self.adjust_content(dedent("""\
            class Cart < ActiveRecord::<2>Base
                act<1>s_as_list
            end
        """)))
        main_path = join(test_dir, main_filename)
        writefile(main_path, main_content)
        main_buf = self.mgr.buf_from_path(main_path)
        pos_targets = [
             ("function", "acts_as_list"),
             ("function", "acts_as_tree"),
             ("function", "acts_as_nested_set"),
             ]
        neg_targets = [
             ("function", "add_child"),
             ]
        self.assertCompletionsInclude2(main_buf, main_positions[1],
                                       pos_targets)
        self.assertCompletionsDoNotInclude(markup_text(main_content,
                                                       pos=main_positions[1]),
                                       neg_targets)


    @tag("global")
    def test_railsenv_model_toplevel_context(self):
        test_dir = join(self.test_dir, "railsapp01", "app", "models")
        main_filename = "cart1.rb"
        main_content, main_positions = \
          unmark_text(self.adjust_content(dedent("""\
            class Cart < ActiveRecord::Base
                val<1>
                def switch
                    des<2>troy
                end
            end
        """)))
        main_path = join(test_dir, main_filename)
        writefile(main_path, main_content)
        main_buf = self.mgr.buf_from_path(main_path)
        class_targets = [
            ("function", "validate"),
            ("function", "validate_find_options"),
            ("function", "validate_on_create"),
            ("function", "validate_on_update"),
            ("function", "validates_acceptance_of"),
            ("function", "validates_associated"),
            ("function", "validates_confirmation_of"),
            ("function", "validates_each"),
            ("function", "validates_exclusion_of"),
            ("function", "validates_format_of"),
            ("function", "validates_inclusion_of"),
            ("function", "validates_length_of"),
            ("function", "validates_numericality_of"),
            ("function", "validates_presence_of"),
            ("function", "validates_size_of"),
            ("function", "validates_uniqueness_of"),
             ]
        inst_targets = [
             ("function", "destroy"),
             ("function", "destroy_all"),
             ]
        self.assertCompletionsInclude2(main_buf, main_positions[1],
                                        class_targets)
        self.assertCompletionsInclude2(main_buf, main_positions[2],
                                       inst_targets)
        self.assertCompletionsDoNotInclude(markup_text(main_content,
                                                       pos=main_positions[1]),
                                       inst_targets)
        self.assertCompletionsDoNotInclude(markup_text(main_content,
                                                       pos=main_positions[2]),
                                       class_targets)


    def test_railsenv_controller_basic(self):
        test_dir = join(self.test_dir, "railsapp01", "app", "controllers")
        main_filename = "admin_controller.rb"
        main_content, main_positions = \
          unmark_text(self.adjust_content(dedent("""\
            class ApplicationController < ActionController::<1>Base
                ApplicationController.<2>after_filter :check_authentication, :except => [:signin]
                def signin 
                    self.<3>render(:layout, "sheep".<4>pluralize)
                end
            end
        """)))
        main_path = join(test_dir, main_filename)
        writefile(main_path, main_content)
        main_buf = self.mgr.buf_from_path(main_path)
        targets = [[("class", "Base"),],
             [("function", "after_filter"),],
             [("function", "render"),],
             [("function", "pluralize"),],
             ]
        for i in range(len(targets)):
            self.assertCompletionsInclude2(main_buf, main_positions[i + 1],
                                           targets[i])
            ## Verify we don't get false hits
            self.assertCompletionsDoNotInclude(markup_text(main_content,
                                                           pos=main_positions[i + 1]),
                                               targets[i])

    def test_railsenv_controller_find_peer(self):
        test_dir = join(self.test_dir, "railsapp01", "app", "controllers")
        adminc_filename = "admin_controller%s" % self.ext
        adminc_content, adminc_positions = \
          unmark_text(self.adjust_content(dedent("""\
            module AppBogus
                # to force a choice at point 2
            end
            class AdminController < <1>App<2>licationController
                aft<3>er_filter :check_authentication, :except => [:signin]
                AdminController.filter_parameter_logging(<6>'a', 'b')
                def open
                    exp<4>ires_in 10.seconds
                    self.<5>redirect_to("chumley")
                end
            end
        """)))
        manifest = [
            (join(test_dir, "application.rb"), dedent("""\
                class ApplicationController < ActionController::Base
                    def foo
                    end
                end
             """)),
            (adminc_filename, adminc_content),
        ]
        for file, content in manifest:
            path = join(test_dir, file)
            writefile(path, content)
        adminc_buf = self.mgr.buf_from_path(join(test_dir, adminc_filename))
        targets = [None, #0
                   None, #1
                   [("class", "ApplicationController"), #2
                    ("namespace", "AppBogus"),
                    ],
                   [("function", "after_filter"), #3
                   ],
                   [("function", "expires_in"), #4
                    ("function", "expires_now")
                   ],
                   [("function", "redirect_to"), #5
                    ("function", "session_enabled?"),
                   ],
                  ]
                   
        #for i in range(2, 1 + len(targets)):
        for i in (2, 5):
            self.assertCompletionsInclude2(adminc_buf, adminc_positions[i],
                                           targets[i])
        self.assertCalltipIs2(adminc_buf, adminc_positions[6],
                              dedent("""\
    (*filter_words, &block) {|key, value| ...}
    Replace sensitive paramater data from the request log.
    Filters paramaters that have any of the arguments as a
    substring. Looks in all subhashes of the param hash for keys
    to filter. If a block is given, each key and value of the
    paramater hash and all subhashes is passed to it, the value
    or key can be replaced using String#replace or similar
    method."""))


    @tag("bug65336", "knownfailure")
    # This test *sometimes* fails.
    # This test models how the behaviour described in bug 65336
    # is supposed to work
    def test_controller_deleting_peer(self):
        dirs1 = [self.test_dir, "bug65336", "app"]
        test_controller_dir = join(*(dirs1 + ["controllers"]))
        test_model_dir = join(*(dirs1 + ["models"]))
        adminc_filename = join(test_controller_dir, "admin_controller.rb")
        book_path = join(test_model_dir, "book.rb")
        cart_path = join(test_model_dir, "cart.rb")
        adminc_content, adminc_positions = \
          unmark_text(self.adjust_content(dedent("""\
                class ApplicationController < ActionController::Base
                    def foo
                       x = Cart<5>.<1>new
                       x.<2>add_i<6>tem()
                       y = Boo<7>k.<3>new
                       y.<4>re<8>ad()
                    end
                end
        """)))
        manifest = [
            (cart_path, dedent("""\
                 class Cart < ActiveRecord::Base
                   def add_item(a)
                   end
                 end
             """)),
            (book_path, dedent("""\
                 class Book < ActiveRecord::Base
                   def read(a)
                   end
                 end
             """)),
            (adminc_filename, adminc_content),
        ]
        for path, content in manifest:
            writefile(path, content)
        adminc_buf = self.mgr.buf_from_path(adminc_filename)
        targets = [None, #0
                   [("function", "new"), #1
                    ],
                   [("function", "add_item"), #2
                   ],
                   [("function", "new"), #3
                    ],
                   [("function", "read"), #4
                   ],
                  ]
        for i in range(1, len(targets)):
            self.assertCompletionsInclude2(adminc_buf, adminc_positions[i],
                                           targets[i])
        self.assertDefnMatches2(adminc_buf, adminc_positions[5],
                                ilk="class", name="Cart", line=1)
        self.assertDefnMatches2(adminc_buf, adminc_positions[6],
                                ilk="function", name="add_item", line=2)
        self.assertDefnMatches2(adminc_buf, adminc_positions[7],
                                ilk="class", name="Book", line=1)
        self.assertDefnMatches2(adminc_buf, adminc_positions[8],
                                ilk="function", name="read", line=2)
        os.unlink(book_path)
        
        # Rebuild and scan the controller buffer with the book file deleted.
        adminc_content, adminc_positions = \
          unmark_text(self.adjust_content(dedent("""\
                class ApplicationController < ActionController::Base
                    def updated_funcname  # Force rescan
                       x = Cart.<1>new
                       x.<2>add_item()
                       y = Book.<3>new
                       y.<4>read()
                    end
                end
        """)))
        writefile(adminc_filename, adminc_content)
        adminc_buf = self.mgr.buf_from_path(adminc_filename)
        for i in (1,2):
            self.assertCompletionsInclude2(adminc_buf, adminc_positions[i],
                                           targets[i])
        # These two tests fail.
        for i in (3,4):
            self.assertCompletionsAre2(adminc_buf, adminc_positions[i], None)
        
    # Make sure migration files can see the models -- not too useful,
    # as the code-completion will be class-level ActiveRecord only,
    # but we need to know the model names

    @tag("bug68997")
    def test_migration_sees_model(self):
        dirs1 = [self.test_dir, "bug68997", "app"]
        test_model_dir = join(*(dirs1 + ["models"]))
        book_path = join(test_model_dir, "book.rb")
        cart_path = join(test_model_dir, "cart.rb")
        
        dirs2 = [self.test_dir, "bug68997", "db", "migrate"]
        migrate_dir = join(*dirs2)
        migrate_path = join(migrate_dir, "001_create_books.rb")
        migrate_table_create_path = join(migrate_dir, "001_create_books.rb")
        migrate_add_data_path = join(migrate_dir, "002_add_data.rb")
        migrate_content, migrate_positions = \
          unmark_text(self.adjust_content(dedent("""\
                class CreateTitleData < ActiveRecord::Migration
                def self.up
                    Cart.<1>create(:no => 1, :fields => 2, :yet => 3)
                end
                def self.down
                    Cart.<2>delete_all
                end
                end
        """)))
        manifest = [
            (cart_path, dedent("""\
                 class Cart < ActiveRecord::Base
                   def add_item(a)
                   end
                 end
             """)),
            (book_path, dedent("""\
                 class Book < ActiveRecord::Base
                   def read(a)
                   end
                 end
             """)),
            (migrate_table_create_path, dedent("""\
                class CreateTitle < ActiveRecord::Migration
                  def self.up
                    create_table :books do |t|
                      t.column 'title', :string
                      t.column :author, :string
                      t.column "publisher", :string
                      t.column :rating, :float
                    end
                  end
                  def self.down
                  end
                end
             """)),
            (migrate_add_data_path, migrate_content),
        ]
        for path, content in manifest:
            writefile(path, content)
        migrate_buf = self.mgr.buf_from_path(migrate_add_data_path)
        self.assertCompletionsInclude2(migrate_buf, migrate_positions[2],
                                       [("function", "new"),
                                        ("function", "create"),
                                        ("function", "delete_all"),
                                       ])
        self.assertCompletionsInclude2(migrate_buf, migrate_positions[1],
                                       [("function", "new"),
                                        ("function", "create"),
                                        ("function", "delete_all"),
                                       ])        

    @tag("bug68997")
    def test_migration_sees_model(self):
        dirs1 = [self.test_dir, "bug68997b", "app"]
        test_model_dir = join(*(dirs1 + ["models"]))
        book_path = join(test_model_dir, "book.rb")
        cart_path = join(test_model_dir, "cart.rb")
        
        dirs2 = [self.test_dir, "bug68997b", "db", "migrate"]
        migrate_dir = join(*dirs2)
        migrate_path = join(migrate_dir, "001_create_books.rb")
        migrate_table_create_path = join(migrate_dir, "001_create_books.rb")
        migrate_add_data_path = join(migrate_dir, "002_add_data.rb")
        migrate_content, migrate_positions = \
          unmark_text(self.adjust_content(dedent("""\
                class CreateTitleData < ActiveRecord::Migration
                def self.up
                    Cart.<1>create(:no => 1, :fields => 2, :yet => 3)
                end
                def self.down
                    Cart.<2>delete_all
                end
                end
        """)))
        manifest = [
            (cart_path, dedent("""\
                 class Cart < ActiveRecord::Base
                   def add_item(a)
                   end
                 end
             """)),
            (book_path, dedent("""\
                 class Book < ActiveRecord::Base
                   def read(a)
                   end
                 end
             """)),
            (migrate_table_create_path, dedent("""\
                class CreateTitle < ActiveRecord::Migration
                  def self.up
                    create_table :books do |t|
                      t.column 'title', :string
                      t.column :author, :string
                      t.column "publisher", :string
                      t.column :rating, :float
                    end
                  end
                  def self.down
                  end
                end
             """)),
            (migrate_add_data_path, migrate_content),
        ]
        for path, content in manifest:
            writefile(path, content)
        migrate_buf = self.mgr.buf_from_path(migrate_add_data_path)
        self.assertCompletionsInclude2(migrate_buf, migrate_positions[2],
                                       [("function", "new"),
                                        ("function", "create"),
                                        ("function", "delete_all"),
                                       ])
        self.assertCompletionsInclude2(migrate_buf, migrate_positions[1],
                                       [("function", "new"),
                                        ("function", "create"),
                                        ("function", "delete_all"),
                                       ])        

    @tag("bug69532",  "railstests")
    def test_functional_test_sees_model(self):
        dirs1 = [self.test_dir, "bug69532", "app"]
        test_model_dir = join(*(dirs1 + ["models"]))
        book_path = join(test_model_dir, "book.rb")
        cart_path = join(test_model_dir, "cart.rb")
        
        migrate_dir = join(self.test_dir, "bug69532", "db", "migrate")
        book_migrate_path = join(migrate_dir, "001_create_books.rb")
        cart_migrate_path = join(migrate_dir, "002_create_cart.rb")        
        
        dirs2 = [self.test_dir, "bug69532", "test", "unit"]
        unit_dir = join(*dirs2)
        unit_book_path = join(unit_dir, "book_test.rb")
        unit_content, unit_positions = \
          unmark_text(self.adjust_content(dedent("""\                                                 
                require File.dirname(__FILE__) + '/../test_helper'
                
                class BookTest < Test::Unit::TestCase
                  fixtures :books
                  # Replace this with your real tests.
                  def test_make_book
                     roots = Book.<1>new
                     horse = Cart.<2>new
                     roots.<3>read
                     horse.<4>add_item
                     puts roots.<5>publisher + horse.<6>contents
                  end
                end
        """)))
        manifest = [
            (cart_path, dedent("""\
                 class Cart < ActiveRecord::Base
                   def add_item(a)
                   end
                 end
             """)),
            (book_path, dedent("""\
                 class Book < ActiveRecord::Base
                   def read(a)
                   end
                 end
             """)),
            (book_migrate_path, dedent("""\
                  def self.up
                    create_table :books do |t|
                      t.column 'title', :string
                      t.column :author, :string
                      t.column "publisher", :string
                      t.column :rating, :float
                    end
                    create_table :dishes do |t|
                      t.column 'year', :string
                      t.column :manufacturer, :string
                    end
                    create_table :books do |t|
                      t.column 'isbn', :string
                    end
                  end
                  def self.down
                  end
             """)),
            (cart_migrate_path, dedent("""\
                  def self.up
                    create_table :carts do |t|
                      t.column 'owner', :string
                      t.column :contents, :string
                      t.column "created_on", :datetime
                    end
                  end
                  def self.down
                  end
             """)),
            (unit_book_path, unit_content),
        ]
        for path, content in manifest:
            writefile(path, content)
        unit_buf = self.mgr.buf_from_path(unit_book_path)
        self.assertCompletionsInclude2(unit_buf, unit_positions[1],
                                       [("function", "new"),
                                        #("function", "create"),
                                        #("function", "delete_all"),
                                       ])
        self.assertCompletionsInclude2(unit_buf, unit_positions[2],
                                       [("function", "new"),
                                        #("function", "create"),
                                        #("function", "delete_all"),
                                       ])
        self.assertCompletionsInclude2(unit_buf, unit_positions[3],
                                       [("function", "read"),
                                       ])
        self.assertCompletionsInclude2(unit_buf, unit_positions[4],
                                       [("function", "add_item"),
                                       ])


    @tag("bug69532", "knownfailure", "railstests")
    def test_functional_test_sees_migrations(self):
        dirs1 = [self.test_dir, "bug69532", "app"]
        test_model_dir = join(*(dirs1 + ["models"]))
        book_path = join(test_model_dir, "book.rb")
        cart_path = join(test_model_dir, "cart.rb")
        
        migrate_dir = join(self.test_dir, "bug69532", "db", "migrate")
        book_migrate_path = join(migrate_dir, "001_create_books.rb")
        cart_migrate_path = join(migrate_dir, "002_create_cart.rb")        
        
        dirs2 = [self.test_dir, "bug69532", "test", "unit"]
        unit_dir = join(*dirs2)
        unit_book_path = join(unit_dir, "book_test.rb")
        unit_content, unit_positions = \
          unmark_text(self.adjust_content(dedent("""\                                                 
                require File.dirname(__FILE__) + '/../test_helper'
                
                class BookTest < Test::Unit::TestCase
                  fixtures :books
                  # Replace this with your real tests.
                  def test_make_book
                     roots = Book.<1>new
                     horse = Cart.<2>new
                     roots.<3>read
                     horse.<4>add_item
                     puts roots.<5>publisher + horse.<6>contents
                  end
                end
        """)))
        manifest = [
            (cart_path, dedent("""\
                 class Cart < ActiveRecord::Base
                   def add_item(a)
                   end
                 end
             """)),
            (book_path, dedent("""\
                 class Book < ActiveRecord::Base
                   def read(a)
                   end
                 end
             """)),
            (book_migrate_path, dedent("""\
                  def self.up
                    create_table :books do |t|
                      t.column 'title', :string
                      t.column :author, :string
                      t.column "publisher", :string
                      t.column :rating, :float
                    end
                    create_table :dishes do |t|
                      t.column 'year', :string
                      t.column :manufacturer, :string
                    end
                    create_table :books do |t|
                      t.column 'isbn', :string
                    end
                  end
                  def self.down
                  end
             """)),
            (cart_migrate_path, dedent("""\
                  def self.up
                    create_table :carts do |t|
                      t.column 'owner', :string
                      t.column :contents, :string
                      t.column "created_on", :datetime
                    end
                  end
                  def self.down
                  end
             """)),
            (unit_book_path, unit_content),
        ]
        for path, content in manifest:
            writefile(path, content)
        unit_buf = self.mgr.buf_from_path(unit_book_path)
        self.assertCompletionsInclude2(unit_buf, unit_positions[5],
                                       [("function", "publisher"),
                                       ])
        self.assertCompletionsInclude2(unit_buf, unit_positions[6],
                                       [("function", "contents"),
                                       ])

    @tag("bug65443")
    def test_model_sees_migrations(self):
        dirs1 = [self.test_dir, "bug65443", "app"]
        test_model_dir = join(*(dirs1 + ["models"]))
        book_path = join(test_model_dir, "book.rb")
        
        dirs2 = [self.test_dir, "bug65443", "db", "migrate"]
        migrate_dir = join(*dirs2)
        migrate_path = join(migrate_dir, "001_create_books.rb")
        migrate_table_create_path = join(migrate_dir, "001_create_books.rb")
        migrate_add_column_path = join(migrate_dir, "002_add_book_items.rb")
        model_content, model_positions = \
          unmark_text(self.adjust_content(dedent("""\
                 class Book < ActiveRecord::Base
                   def get_title(a)
                       return self.<1>title
                   end
                 end
        """)))
        manifest = [
            (migrate_table_create_path, dedent("""\
                class Book < ActiveRecord::Migration
                  def self.up
                    create_table :books do |t|
                      t.column 'title', :string
                      t.column :author, :string
                      t.column "publisher", :string
                      t.column :rating, :float
                    end
                    create_table :dishes do |t|
                      t.column 'year', :string
                      t.column :manufacturer, :string
                    end
                    create_table :books do |t|
                      t.column 'isbn', :string
                    end
                  end
                  def self.down
                  end
                end
             """)),
            (migrate_add_column_path, dedent("""\
                class Book < ActiveRecord::Migration
                  def self.up
                    add_column :books, "typeface", :string
                    add_column :bookies, "bet", :string
                    add_column 'books', :year, :string
                  end
                  def self.down
                  end
                end
             """)),
            (book_path, model_content),
        ]
        for path, content in manifest:
            writefile(path, content)
        model_buf = self.mgr.buf_from_path(book_path)
        self.assertCompletionsInclude2(model_buf, model_positions[1],
                                       [("function", "title"),
                                        ("function", "author"),
                                        ("function", "publisher"),
                                        ("function", "isbn"),
                                        ("function", "rating"),
                                        ("function", "typeface"),
                                        ("function", "year"),
                                       ])
        self.assertCompletionsDoNotInclude2(model_buf, model_positions[1],
                                       [("function", "bet"),
                                       ])
    
    books_and_dishes_migration = dedent("""\
        class Book < ActiveRecord::Migration
          def self.up
            create_table :dishes do |t|
              t.integer 'year'
              t.string :manufacturer
              t.timestamps
            end
            create_table :books do |t|
              t.string 'title'
              t.string :author
              t.string "publisher"
            end
            create_table :books do |t|
              t.column 'isbn', :string
            end
          end
          def self.down
          end
        end
     """)
    
    @tag("bug75440")
    def test_model_sees_rails2_migrations_1(self):
        dirs1 = [self.test_dir, "bug75440", "app"]
        test_model_dir = join(*(dirs1 + ["models"]))
        book_path = join(test_model_dir, "book.rb")
        
        dirs2 = [self.test_dir, "bug75440", "db", "migrate"]
        migrate_dir = join(*dirs2)
        migrate_table_create_path = join(migrate_dir, "001_create_books_and_dishes.rb")
        model_content, model_positions = \
          unmark_text(self.adjust_content(dedent("""\
                 class Book < ActiveRecord::Base
                   def get_title(a)
                       return self.<1>title
                   end
                 end
        """)))
        manifest = [
            (migrate_table_create_path, self.books_and_dishes_migration),
            (book_path, model_content),
        ]
        for path, content in manifest:
            writefile(path, content)
        model_buf = self.mgr.buf_from_path(book_path)
        self.assertCompletionsInclude2(model_buf, model_positions[1],
                                       [("function", "title"),
                                        ("function", "author"),
                                        ("function", "publisher"),
                                        ("function", "isbn"),
                                       ])
        self.assertCompletionsDoNotInclude2(model_buf, model_positions[1],
                                       [("function", "bet"),
                                        ("function", "manufacturer"),
                                        ("function", "created_at"),
                                        ("function", "updated_at"),
                                       ])


    @tag("bug75440")
    def test_model_sees_rails2_migrations_2(self):
        dirs1 = [self.test_dir, "bug75440b", "app"]
        test_model_dir = join(*(dirs1 + ["models"]))
        book_path = join(test_model_dir, "dish.rb")
        
        dirs2 = [self.test_dir, "bug75440b", "db", "migrate"]
        migrate_dir = join(*dirs2)
        migrate_table_create_path = join(migrate_dir, "001_create_books_and_dishes.rb")
        model_content, model_positions = \
          unmark_text(self.adjust_content(dedent("""\
                 class Dish < ActiveRecord::Base
                   def get_plate(a)
                       return self.<1>year
                   end
                 end
        """)))
        manifest = [
            (migrate_table_create_path, self.books_and_dishes_migration),
            (book_path, model_content),
        ]
        for path, content in manifest:
            writefile(path, content)
        model_buf = self.mgr.buf_from_path(book_path)
        # log.error("model_buf=%s", model_buf)
        self.assertCompletionsInclude2(model_buf, model_positions[1],
                                       [("function", "year"),
                                        ("function", "manufacturer"),
                                        ("function", "created_at"),
                                        ("function", "updated_at"),
                                       ])
        self.assertCompletionsDoNotInclude2(model_buf, model_positions[1],
                                       [("function", "shamroobah"),
                                        ("function", "author"),
                                        ("function", "publisher"),
                                        ("function", "title"),
                                       ])


    def test_controller_sees_migrations(self):
        dirs1 = [self.test_dir, "bug68997c", "app"]
        test_model_dir = join(*(dirs1 + ["models"]))
        book_model_path = join(test_model_dir, "book.rb")
        
        test_controller_dir = join(*(dirs1 + ["controllers"]))
        book_controller_path = join(test_controller_dir, "book_controller.rb")
        
        dirs2 = [self.test_dir, "bug68997c", "db", "migrate"]
        migrate_dir = join(*dirs2)
        migrate_path = join(migrate_dir, "001_create_books.rb")
        migrate_table_create_path = join(migrate_dir, "001_create_books.rb")
        migrate_add_column_path = join(migrate_dir, "002_add_book_items.rb")
        content, positions = \
          unmark_text(self.adjust_content(dedent("""\
                 class BookController < ApplicationController
                   def create
                    book = Book.new(params[:title])
                    book.<1>title = "splibitsh"
                    book.publisher<2> = "Rodoni"
                   end
                 end
        """)))
        manifest = [
            (migrate_table_create_path, dedent("""\
                class Book < ActiveRecord::Migration
                  def self.up
                    create_table :books do |t|
                      t.column 'title', :string
                      t.column :author, :string
                      t.column "publisher", :string
                      t.column :rating, :float
                    end
                    create_table :dishes do |t|
                      t.column 'year', :string
                      t.column :manufacturer, :string
                    end
                    create_table :books do |t|
                      t.column 'isbn', :string
                    end
                  end
                  def self.down
                  end
                end
             """)),
            (migrate_add_column_path, dedent("""\
                class Book < ActiveRecord::Migration
                  def self.up
                    add_column :books, "typeface", :string
                    add_column :bookies, "bet", :string
                    add_column 'books', :year, :string
                  end
                  def self.down
                  end
                end
             """)),
            (book_model_path, dedent("""\
                 class Book < ActiveRecord::Base
                 end
             """)),
            (book_controller_path, content),
        ]
        for mpath, mcontent in manifest:
            writefile(mpath, mcontent)
        buf = self.mgr.buf_from_path(book_controller_path)
        self.assertCompletionsInclude2(buf, positions[1],
                                       [("function", "title"),
                                        ("function", "author"),
                                        ("function", "publisher"),
                                        ("function", "isbn"),
                                        ("function", "rating"),
                                        ("function", "typeface"),
                                        ("function", "year"),
                                       ])
        self.assertCompletionsDoNotInclude2(buf, positions[1],
                                       [("function", "bet"),
                                       ])
        self.assertDefnMatches2(buf, positions[2], lang="Ruby",
                                line=6,
                                path=migrate_table_create_path
                               )
        
    # This test *sometimes* fails.
    # This test models how the behaviour described in bug 65336
    # is supposed to work
    @tag("failsintermittently")
    def test_controller_find_peer(self):
        dirs1 = [self.test_dir, "peers", "app"]
        test_controller_dir = join(*(dirs1 + ["controllers"]))
        test_model_dir = join(*(dirs1 + ["models"]))
        adminc_filename = join(test_controller_dir, "admin_controller.rb")
        book_path = join(test_model_dir, "book.rb")
        cart_path = join(test_model_dir, "cart.rb")
        adminc_content, adminc_positions = \
          unmark_text(self.adjust_content(dedent("""\
                class ApplicationController < ActionController::Base
                    def foo
                       x = Cart<5>.<1>new
                       x.<2>add_i<6>tem()
                       y = Boo<7>k.<3>new
                       y.<4>re<8>ad()
                    end
                end
        """)))
        manifest = [
            (cart_path, dedent("""\
                 class Cart < ActiveRecord::Base
                   def add_item(a)
                   end
                 end
             """)),
            (book_path, dedent("""\
                 class Book < ActiveRecord::Base
                   def read(a)
                   end
                 end
             """)),
            (adminc_filename, adminc_content),
        ]
        for path, content in manifest:
            writefile(path, content)
        adminc_buf = self.mgr.buf_from_path(adminc_filename)
        targets = [None, #0
                   [("function", "new"), #1
                    ],
                   [("function", "add_item"), #2
                   ],
                   [("function", "new"), #3
                    ],
                   [("function", "read"), #4
                   ],
                  ]
        repl_path = 'models'
        fixed_cart_path = cart_path.replace('models', repl_path)
        fixed_book_path = book_path.replace('models', repl_path)
        self.assertDefnMatches2(adminc_buf, adminc_positions[5],
                                ilk="class", name="Cart", line=1, path=fixed_cart_path)
        self.assertDefnMatches2(adminc_buf, adminc_positions[6],
                                ilk="function", name="add_item", line=2, path=fixed_cart_path)
        self.assertDefnMatches2(adminc_buf, adminc_positions[7],
                                ilk="class", name="Book", line=1, path=fixed_book_path)
        self.assertDefnMatches2(adminc_buf, adminc_positions[8],
                                ilk="function", name="read", line=2, path=fixed_book_path)
        

re_cursor = re.compile(r'<[\|\d]+>')

class MultiLangRailsTestCase(_BaseTestCase):
    lang = "RHTML"
    ext = ".rhtml"
    heredoc_support = False

    _rhtml_prefix = "<body><p><% "
    _rhtml_suffix = " %>"
    def adjust_content(self, content):
        if not re_cursor.search(content):
            content += "<|>"
        return self._rhtml_prefix + content + self._rhtml_suffix
    def adjust_pos(self, pos):
        return pos + len(self._rhtml_prefix)
    
    def test_railsenv_views_basic_contrived(self):
        test_dir = join(self.test_dir, "railsapp01", "app", "views", "layouts")
        main_filename = "add.rhtml"
        main_content, main_positions = \
          unmark_text(self.adjust_content(dedent("""\
            # Contrived: most layouts are implicit members of this class
            class Zoomoo < ActionView::<1>Base 
                Zoomoo.<2>cache_template_extensions
                Zoomoo.new.<3>form_for
                "whatever".<4>pluralize
            end
            h = {'zounds' => 1, 'ok' => 2}
            h.<5>keys
        """)))
        main_path = join(test_dir, main_filename)
        writefile(main_path, main_content)
        main_buf = self.mgr.buf_from_path(main_path)
        targets = [[("class", "Base"),],
             [("function", "cache_template_extensions"),],
             [("function", "form_for"),],
             [("function", "pluralize"),],
             [("function", "stringify_keys!"),],
             ]
        for i in range(len(targets)):
            self.assertCompletionsInclude2(main_buf, main_positions[i + 1],
                                           targets[i])
            ## Verify we don't get false hits
            self.assertCompletionsDoNotInclude(markup_text(main_content,
                                                           pos=main_positions[i + 1]),
                                               targets[i])
    
    @tag("knownfailure", "bug74706")
    def test_railsenv_views_basic_html_erb_suffix(self):
        test_dir = join(self.test_dir, "railsapp01", "app", "views", "layouts")
        main_filename = "add.html.erb"
        main_content, main_positions = \
          unmark_text(self.adjust_content(dedent("""\
            # Contrived: most layouts are implicit members of this class
            class Zoomoo < ActionView::<1>Base 
                Zoomoo.<2>cache_template_extensions
                Zoomoo.new.<3>form_for
                "whatever".<4>pluralize
            end
            h = {'zounds' => 1, 'ok' => 2}
            h.<5>keys
        """)))
        main_path = join(test_dir, main_filename)
        writefile(main_path, main_content)
        main_buf = self.mgr.buf_from_path(main_path)
        targets = [[("class", "Base"),],
             [("function", "cache_template_extensions"),],
             [("function", "form_for"),],
             [("function", "pluralize"),],
             [("function", "stringify_keys!"),],
             ]
        for i in range(len(targets)):
            self.assertCompletionsInclude2(main_buf, main_positions[i + 1],
                                           targets[i])
            ## Verify we don't get false hits
            self.assertCompletionsDoNotInclude(markup_text(main_content,
                                                           pos=main_positions[i + 1]),
                                               targets[i])
    
    @tag("global")
    def test_railsenv_views_basic_realistic(self):
        test_dir = join(self.test_dir, "railsapp01", "app", "views", "layouts")
        main_filename = "add.rhtml"
        main_content, main_positions = \
          unmark_text(self.adjust_content(dedent("""\
            # Contrived: most layouts are implicit members of this class
            h = Act<1>ionView::<2>Base
            for<3>m_for
            "whatever".<4>pluralize
        """)))
        main_path = join(test_dir, main_filename)
        writefile(main_path, main_content)
        main_buf = self.mgr.buf_from_path(main_path)
        targets = [
            [("namespace", "ActionView"),
             ("namespace", "ActiveRecord"),
             ("namespace", "ActionController"),
             ],
            [("class", "Base"),],
             [("function", "form_for"),],
             [("function", "pluralize"),]
             ]
        for i in range(len(targets)):
            self.assertCompletionsInclude2(main_buf, main_positions[i + 1],
                                           targets[i])
            ## Verify we don't get false hits
            self.assertCompletionsDoNotInclude(markup_text(main_content,
                                                           pos=main_positions[i + 1]),
                                               targets[i])
            
    def test_rhtml_calltips(self):
        test_dir = join(self.test_dir, "railsapp01", "app", "views", "admin")
        main_filename = "list.rhtml"
        main_markup = dedent("""\
            <h1>Listing titles</h1>
                <table>
                <% for title in @titles %>
                  <tr>
                    <td align='left'><%= link_to(<1> 'Show', :action => 'show', :id => title) %>
                    <td align='left'><%= link_to_if <2>'Show', :action => 'show', :id => title) %>
                    <td align='left'><%= <$>link<3> %>
                    </td></tr></table>
        """)
        main_content, main_positions = unmark_text(main_markup)
        main_path = join(test_dir, main_filename)
        writefile(main_path, main_content)
        main_buf = self.mgr.buf_from_path(main_path)
        '''
        self.assertCalltipIs2(main_buf, main_positions[1],
                              dedent("""\
                                     (name, options = {}, html_options = nil, *parameters_for_method_reference)"""))
        '''
        self.assertCalltipIs2(main_buf, main_positions[2],
                              dedent("""\
    (condition, name, options = {}, html_options = {}, *parameters_for_method_reference, &block)
    Creates a link tag of the given name</tt> using a URL
    created by the set of <tt>options</tt> if <tt>condition is
    true, in which case only the name is returned. To specialize
    the default behavior, you can pass a block that accepts the
    name or the full argument list for link_to_unless (see the
    examples in link_to_unless)."""))
        self.assertNoPrecedingTrigger(markup_text(main_content,
                                                start_pos=main_positions['start_pos'],
                                                  pos=main_positions[3]))
                                                  
        
#---- mainline

if __name__ == "__main__":
    unittest.main()


