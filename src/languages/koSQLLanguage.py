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

from xpcom import components, ServerException

from koLanguageServiceBase import *

class koCommonSQLLanguage(KoLanguageBase):
    _stateMap = {
        'default': ('SCE_SQL_DEFAULT',),
        'identifiers': ('SCE_SQL_IDENTIFIER',),
        'keywords': ('SCE_SQL_WORD',
                     'SCE_SQL_WORD2',
                     ),
        'comments': ('SCE_SQL_COMMENT',
                     'SCE_SQL_COMMENTLINE',
                     'SCE_SQL_COMMENTLINEDOC',
                     'SCE_SQL_COMMENTDOC',
                     'SCE_SQL_COMMENTDOCKEYWORD',
                     'SCE_SQL_COMMENTDOCKEYWORDERROR',
                     'SCE_SQL_SQLPLUS_COMMENT',
                     ),
        'numbers': ('SCE_SQL_NUMBER',),
        'strings': ('SCE_SQL_STRING',
                    'SCE_SQL_CHARACTER',
                    ),
        'operators': ('SCE_SQL_OPERATOR',),
        }
    commentDelimiterInfo = {
        "line": [ "--" ],
        "block": [ ("/*", "*/") ],
    }
    searchURL = "http://www.google.com/search?q=sql+%W"

    def __init__(self):
        KoLanguageBase.__init__(self)
        self._style_info.update(
            _block_comment_styles = [sci_constants.SCE_SQL_COMMENT]
            )
        del self.matchingSoftChars['"']
        self._fastCharData = \
            FastCharData(trigger_char=";",
                         style_list=(sci_constants.SCE_SQL_OPERATOR,),
                         skippable_chars_by_style={ sci_constants.SCE_SQL_OPERATOR : "])",
                                    })
    
    def get_lexer(self):
        if self._lexer is None:
            self._lexer = KoLexerLanguageService()
            self._lexer.setLexer(components.interfaces.ISciMoz.SCLEX_SQL)
            self._lexer.setKeywords(0, self._keywords)
            self._lexer.supportsFolding = 1
        return self._lexer

class koSQLLanguage(koCommonSQLLanguage):
    name = "SQL"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{EC1B0777-D982-41af-906F-34923D602B72}"
    _reg_categories_ = [("komodo-language", name)]

    defaultExtension = ".sql"

    # LexSQL seems to ignore keywords completely
    # Possible optimization: split on demand
    _keywords = """absolute action add admin after aggregate
        alias all allocate alter and any are array as asc
        assertion at authorization
        before begin binary bit blob boolean both breadth by
        call cascade cascaded case cast catalog char character
        check class clob close collate collation column commit
        completion connect connection constraint constraints
        constructor continue corresponding create cross cube current
        current_date current_path current_role current_time current_timestamp
        current_user cursor cycle
        data date day deallocate dec decimal declare default
        deferrable deferred delete depth deref desc describe descriptor
        destroy destructor deterministic dictionary diagnostics disconnect
        distinct domain double drop dynamic
        each else end end-exec equals escape every except
        exception exec execute external
        false fetch first float for foreign found from free full
        function
        general get global go goto grant group grouping
        having host hour
        identity if ignore immediate in indicator initialize initially
        inner inout input insert int integer intersect interval
        into is isolation iterate
        join
        key
        language large last lateral leading left less level like
        limit local localtime localtimestamp locator
        map match minute modifies modify module month
        names national natural nchar nclob new next no none
        not null numeric
        object of off old on only open operation option
        or order ordinality out outer output
        pad parameter parameters partial path postfix precision prefix
        preorder prepare preserve primary
        prior privileges procedure public
        read reads real recursive ref references referencing relative
        restrict result return returns revoke right
        role rollback rollup routine row rows
        savepoint schema scroll scope search second section select
        sequence session session_user set sets size smallint some| space
        specific specifictype sql sqlexception sqlstate sqlwarning start
        state statement static structure system_user
        table temporary terminate than then time timestamp
        timezone_hour timezone_minute to trailing transaction translation
        treat trigger true
        under union unique unknown
        unnest update usage user using
        value values varchar variable varying view
        when whenever where with without work write
        year
        zone""".split()

class koPLSQLLanguage(koSQLLanguage):
    name = "PL-SQL"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{543492ec-bdb7-4724-b4ea-482b777d07b4}"
    _reg_categories_ = [("komodo-language", name)]
    defaultExtension = ".plsql"

    # These keywords are a union of the list in
    # http://www.uwex.edu/infosys/oraprod/reserved/ and the list supplied by
    # gsalem at http://community.activestate.com/forum-topic/pl-sql-coide-intelligence
    # in his xpi file ()
    # Possible optimization: split on demand
    _keywords = """a
abort
access
accessed
account
activate
add
admin
administer
administrator
advise
advisor
after
algorithm
alias
all
all_rows
allocate
allow
alter
always
analyze
ancillary
and
and_equal
antijoin
any
append
apply
archive
archivelog
array
as
asc
associate
at
attribute
attributes
audit
authenticated
authentication
authid
authorization
auto
autoallocate
autoextend
automatic
availability
backup
batch
become
before
begin
begin_outline_data
behalf
between
bfile
bigfile
binary_double
binary_double_infinity
binary_double_nan
binary_float
binary_float_infinity
binary_float_nan
binding
bitmap
bitmap_tree
bitmaps
bits
blob
block
block_range
blocks
blocksize
body
both
bound
broadcast
buffer
buffer_cache
buffer_pool
build
bulk
by
bypass_recursive_check
bypass_ujvc
byte
cache
cache_cb
cache_instances
cache_temp_table
call
cancel
cardinality
cascade
case
cast
category
certificate
cfile
chained
change
char
char_cs
character
check
checkpoint
child
choose
chunk
civ_gb
class
clear
clob
clone
close
close_cached_open_cursors
cluster
clustering_factor
coalesce
coarse
collect
collections_get_refs
column
column_stats
column_value
columns
comment
commit
committed
compact
compatibility
compile
complete
composite_limit
compress
compute
conforming
connect
connect_by_cost_based
connect_by_filtering
connect_by_iscycle
connect_by_isleaf
connect_by_root
connect_time
consider
consistent
constant
constraint
constraints
container
content
contents
context
continue
controlfile
convert
corruption
cost
cpu_costing
cpu_per_call
cpu_per_session
create
create_stored_outlines
cross
cube
cube_gb
current
current_date
current_schema
current_time
current_timestamp
current_user
cursor
cursor_sharing_exact
cursor_specific_segment
cycle
dangling
data
database
datafile
datafiles
dataobjno
date
date_mode
day
db_role_change
dba
dba_recyclebin
dbms_stats
dbtimezone
ddl
deallocate
debug
dec
decimal
declare
decrement
decrypt
default
deferrable
deferred
defined
definer
degree
delay
delete
demand
dense_rank
dequeue
deref
deref_no_rewrite
desc
detached
determines
dictionary
dimension
directory
disable
disable_rpke
disassociate
disconnect
disk
diskgroup
disks
dismount
distinct
distinguished
distributed
dml
dml_update
document
domain_index_no_sort
domain_index_sort
double
downgrade
driving_site
drop
dump
dynamic
dynamic_sampling
dynamic_sampling_est_cdn
each
element
eliminate_join
eliminate_oby
eliminate_outer_join
else
empty
enable
encrypt
encrypted
encryption
end
end_outline_data
enforce
enforced
enqueue
enterprise
entry
error
error_on_overlap_time
errors
escape
estimate
evalname
evaluation
events
except
exceptions
exchange
excluding
exclusive
execute
exempt
exists
expand_gset_to_union
expire
explain
explosion
export
expr_corr_check
extend
extends
extent
extents
external
externally
extract
fact
failed
failed_login_attempts
failgroup
false
fast
fbtscan
fic_civ
fic_piv
file
filter
final
fine
finish
first
first_rows
flagger
flashback
float
flob
flush
following
for
force
force_xml_query_rewrite
foreign
freelist
freelists
freepools
fresh
from
full
function
functions
gather_plan_statistics
gby_conc_rollup
generated
global
global_name
global_topic_enabled
globally
grant
group
group_by
grouping
groups
guarantee
guaranteed
guard
hash
hash_aj
hash_sj
hashkeys
having
header
heap
hierarchy
high
hintset_begin
hintset_end
hour
hwm_brokered
id
identified
identifier
identity
idgenerators
idle_time
if
ignore
ignore_on_clause
ignore_optim_embedded_hints
ignore_where_clause
immediate
import
in
in_memory_metadata
include_version
including
increment
incremental
index
index_asc
index_combine
index_desc
index_ffs
index_filter
index_join
index_rows
index_rrs
index_rs
index_rs_asc
index_rs_desc
index_scan
index_skip_scan
index_ss
index_ss_asc
index_ss_desc
index_stats
indexed
indexes
indextype
indextypes
indicator
infinite
informational
initial
initialized
initially
initrans
inline
inline_xmltype_nt
inner
insert
instance
instances
instantiable
instantly
instead
int
integer
integrity
intermediate
internal_convert
internal_use
interpreted
intersect
interval
into
invalidate
is
isolation
isolation_level
iterate
iteration_number
java
job
join
keep
kerberos
key
key_length
keyfile
keys
keysize
kill
last
lateral
layer
ldap_reg_sync_interval
ldap_registration
ldap_registration_enabled
leading
left
length
less
level
levels
library
like
like2
like4
like_expand
likec
limit
link
list
lob
local
local_indexes
localtime
localtimestamp
location
locator
lock
locked
log
logfile
logging
logical
logical_reads_per_call
logical_reads_per_session
logoff
logon
long
main
manage
managed
management
manual
mapping
master
matched
materialize
materialized
max
maxarchlogs
maxdatafiles
maxextents
maximize
maxinstances
maxlogfiles
maxloghistory
maxlogmembers
maxsize
maxtrans
maxvalue
measures
member
memory
merge
merge_aj
merge_const_on
merge_sj
method
migrate
min
minextents
minimize
minimum
minus
minus_null
minute
minvalue
mirror
mlslabel
mode
model
model_compile_subquery
model_dontverify_uniqueness
model_dynamic_subquery
model_min_analysis
model_no_analysis
model_pby
model_push_ref
modify
monitoring
month
mount
move
movement
multiset
mv_merge
name
named
nan
national
native
native_full_outer_join
natural
nav
nchar
nchar_cs
nclob
needed
nested
nested_table_fast_insert
nested_table_get_refs
nested_table_id
nested_table_set_refs
nested_table_set_setid
network
never
new
next
nl_aj
nl_sj
nls_calendar
nls_characterset
nls_comp
nls_currency
nls_date_format
nls_date_language
nls_iso_currency
nls_lang
nls_language
nls_length_semantics
nls_nchar_conv_excp
nls_numeric_characters
nls_sort
nls_special_chars
nls_territory
no
no_access
no_basetable_multimv_rewrite
no_buffer
no_cartesian
no_connect_by_cost_based
no_connect_by_filtering
no_cpu_costing
no_eliminate_join
no_eliminate_oby
no_eliminate_outer_join
no_expand
no_expand_gset_to_union
no_fact
no_filtering
no_index
no_index_ffs
no_index_rs
no_index_ss
no_merge
no_model_push_ref
no_monitoring
no_multimv_rewrite
no_native_full_outer_join
no_order_rollups
no_parallel
no_parallel_index
no_partial_commit
no_prune_gsets
no_pull_pred
no_push_pred
no_push_subq
no_px_join_filter
no_qkn_buff
no_query_transformation
no_ref_cascade
no_rewrite
no_semijoin
no_set_to_join
no_sql_tune
no_star_transformation
no_stats_gsets
no_swap_join_inputs
no_temp_table
no_unnest
no_use_hash
no_use_hash_aggregation
no_use_merge
no_use_nl
no_xml_dml_rewrite
no_xml_query_rewrite
noappend
noarchivelog
noaudit
nocache
nocompress
nocpu_costing
nocycle
nodelay
noforce
noguarantee
nologging
nomapping
nomaxvalue
nominimize
nominvalue
nomonitoring
none
noorder
nooverride
noparallel
noparallel_index
norely
norepair
noresetlogs
noreverse
norewrite
normal
norowdependencies
nosegment
nosort
nostrict
noswitch
not
nothing
notification
novalidate
nowait
null
nulls
num_index_keys
number
numeric
nvarchar2
object
objno
objno_reuse
of
off
offline
oid
oidindex
old
old_push_pred
on
online
only
opaque
opaque_transform
opaque_xcanonical
opcode
open
operator
opt_estimate
opt_param
optimal
optimizer_features_enable
optimizer_goal
option
or
or_expand
ora_rowscn
order
ordered
ordered_predicates
ordinality
organization
out_of_line
outer
outline
outline_leaf
over
overflow
overflow_nomove
overlaps
own
package
packages
parallel
parallel_index
parameters
parent
parity
partially
partition
partition_hash
partition_list
partition_range
partitions
passing
password
password_grace_time
password_life_time
password_lock_time
password_reuse_max
password_reuse_time
password_verify_function
path
paths
pctfree
pctincrease
pctthreshold
pctused
pctversion
percent
performance
permanent
pfile
physical
piv_gb
piv_ssf
plan
plsql_ccflags
plsql_code_type
plsql_debug
plsql_optimize_level
plsql_warnings
point
policy
post_transaction
power
pq_distribute
pq_map
pq_nomap
prebuilt
preceding
precision
precompute_subquery
prepare
present
preserve
preserve_oid
primary
prior
private
private_sga
privilege
privileges
procedure
profile
program
project
protected
protection
public
pull_pred
purge
push_pred
push_subq
px_granule
px_join_filter
qb_name
query
query_block
queue
queue_curr
queue_rowp
quiesce
quota
random
range
rapidly
raw
rba
rbo_outline
read
reads
real
rebalance
rebuild
records_per_block
recover
recoverable
recovery
recycle
recyclebin
reduced
redundancy
ref
ref_cascade_cursor
reference
referenced
references
referencing
refresh
regexp_like
register
reject
rekey
relational
rely
remote_mapped
rename
repair
replace
required
reset
resetlogs
resize
resolve
resolver
resource
restore
restore_as_intervals
restrict
restrict_all_ref_cons
restricted
resumable
resume
retention
return
returning
reuse
reverse
revoke
rewrite
rewrite_or_error
right
role
roles
rollback
rolling
rollup
row
row_length
rowdependencies
rowid
rownum
rows
rule
rules
salt
sample
save_as_intervals
savepoint
sb4
scale
scale_rows
scan
scan_instances
scheduler
schema
scn
scn_ascending
scope
sd_all
sd_inhibit
sd_show
second
security
seed
seg_block
seg_file
segment
select
selectivity
semijoin
semijoin_driver
sequence
sequenced
sequential
serializable
servererror
session
session_cached_cursors
sessions_per_user
sessiontimezone
sessiontzname
set
set_to_join
sets
settings
severe
share
shared
shared_pool
shrink
shutdown
siblings
sid
simple
single
singletask
size
skip
skip_ext_optimizer
skip_unq_unusable_idx
skip_unusable_indexes
smallfile
smallint
snapshot
some
sort
source
space
specification
spfile
split
spreadsheet
sql
sql_trace
sqlldr
standalone
standby
star
star_transformation
start
startup
statement_id
static
statistics
stop
storage
store
streams
strict
string
strip
structure
submultiset
subpartition
subpartition_rel
subpartitions
subqueries
substitutable
successful
summary
supplemental
suspend
swap_join_inputs
switch
switchover
synonym
sys_dl_cursor
sys_fbt_insdel
sys_op_bitvec
sys_op_cast
sys_op_col_present
sys_op_enforce_not_null
sys_op_extract
sys_op_mine_value
sys_op_noexpand
sys_op_ntcimg
sys_parallel_txn
sys_rid_order
sysaux
sysdate
sysdba
sysoper
system
systimestamp
table
table_stats
tables
tablespace
tablespace_no
tabno
temp_table
tempfile
template
temporary
test
than
the
then
thread
through
time
time_zone
timeout
timestamp
timezone_abbr
timezone_hour
timezone_minute
timezone_offset
timezone_region
tiv_gb
tiv_ssf
to
to_char
toplevel
trace
tracing
tracking
trailing
transaction
transitional
treat
trigger
triggers
true
truncate
trusted
tuning
tx
type
types
tz_offset
ub2
uba
uid
unarchived
unbound
unbounded
under
undo
undrop
uniform
union
unique
unlimited
unlock
unnest
unpacked
unprotected
unquiesce
unrecoverable
until
unusable
unused
upd_indexes
upd_joinindex
updatable
update
updated
upgrade
upsert
urowid
usage
use
use_anti
use_concat
use_hash
use_hash_aggregation
use_merge
use_nl
use_nl_with_index
use_private_outlines
use_semi
use_stored_outlines
use_ttt_for_gsets
use_weak_name_resl
user
user_defined
user_recyclebin
users
using
validate
validation
value
values
varchar
varchar2
varray
varying
vector_read
vector_read_trace
version
versions
view
wait
wallet
wellformed
when
whenever
where
whitespace
with
within
without
work
wrapped
write
x_dyn_prune
xid
xml_dml_rwt_stmt
xmlattributes
xmlcolattval
xmlelement
xmlforest
xmlnamespaces
xmlparse
xmlpi
xmlquery
xmlroot
xmlschema
xmlserialize
xmltable
xmltype
year
yes
zone
""".split()

    def get_lexer(self):
        if self._lexer is None:
            koSQLLanguage.get_lexer(self)
            # kw_sqlplus : keywordlists[3]
            self._lexer.setKeywords(3, ["rem~ark"])
        return self._lexer
            
class koMySQLLanguage(koCommonSQLLanguage):
    name = "MySQL"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{B471580A-2DD7-4AF6-A244-5B95B1B08CF7}"
    _reg_categories_ = [("komodo-language", name)]

    defaultExtension = ".mysql"
    
    # From http://dev.mysql.com/doc/mysqld-version-reference/en/mysqld-version-reference-reservedwords-5-0.html
    _keywords = """add
all
alter
analyze
and
as
asc
asensitive
before
between
bigint
binary
blob
both
by
call
cascade
case
change
char
character
check
collate
column
columns[a]
condition
connection[b]
constraint
continue
convert
create
cross
current_date
current_time
current_timestamp
current_user
cursor
database
databases
day_hour
day_microsecond
day_minute
day_second
dec
decimal
declare
default
delayed
delete
desc
describe
deterministic
distinct
distinctrow
div
double
drop
dual
each
else
elseif
enclosed
escaped
exists
exit
explain
false
fetch
fields[c]
float
float4
float8
for
force
foreign
from
fulltext
goto[d]
grant
group
having
high_priority
hour_microsecond
hour_minute
hour_second
if
ignore
in
index
infile
inner
inout
insensitive
insert
int
int1
int2
int3
int4
int8
integer
interval
into
is
iterate
join
key
keys
kill
label[e]
leading
leave
left
like
limit
lines
load
localtime
localtimestamp
lock
long
longblob
longtext
loop
low_priority
match
mediumblob
mediumint
mediumtext
middleint
minute_microsecond
minute_second
mod
modifies
natural
not
no_write_to_binlog
null
numeric
on
optimize
option
optionally
or
order
out
outer
outfile
precision
primary
privileges[f]
procedure
purge
read
reads
real
references
regexp
release[g]
rename
repeat
replace
require
restrict
return
revoke
right
rlike
schema
schemas
second_microsecond
select
sensitive
separator
set
show
smallint
soname
spatial
specific
sql
sqlexception
sqlstate
sqlwarning
sql_big_result
sql_calc_found_rows
sql_small_result
ssl
starting
straight_join
table
tables[h]
terminated
then
tinyblob
tinyint
tinytext
to
trailing
trigger
true
undo
union
unique
unlock
unsigned
update
upgrade[i]
usage
use
using
utc_date
utc_time
utc_timestamp
values
varbinary
varchar
varcharacter
varying
when
where
while
with
write
xor
year_month
zerofill""".split()

    
    def __init__(self):
        koCommonSQLLanguage.__init__(self)
        # See http://dev.mysql.com/doc/refman/5.0/en/comments.html:
        # MySQL comments need a space after the '--'
        # Copy the delimiter to avoid changing the base classes' delimiter info
        self.commentDelimiterInfo = self.commentDelimiterInfo.copy()
        self.commentDelimiterInfo["line"] = ["-- "]
        
