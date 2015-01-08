# confvars.sh - configure defaults for komodo, Gecko 24
MOZ_UPDATER=1
MOZ_HELP_VIEWER=1
MOZ_APP_NAME=komodo
MOZ_APP_VENDOR=ActiveState
MOZ_APP_BASENAME=komodo
# MOZ_APP_DISPLAYNAME is used to set the .app name - i.e. Komodo.app
MOZ_APP_DISPLAYNAME=Komodo
# MOZ_APP_UA_NAME is used for auto-updates and user agent in web requests.
MOZ_APP_UA_NAME=KomodoEdit
MOZ_KOMODO=1
MOZ_EXTENSION_MANAGER=1
MOZ_PROFILE_MIGRATOR=1
# The application.ini will get defined and included into komodo automatically.
MOZ_APP_STATIC_INI=1

# Enable generational GC?
JSGC_GENERATIONAL=1

# Things we don't really need but upstream wants
MOZ_MEDIA_NAVIGATOR=1
