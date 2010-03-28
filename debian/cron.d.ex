#
# Regular cron jobs for the minex package
#
0 4	* * *	root	[ -x /usr/bin/minex_maintenance ] && /usr/bin/minex_maintenance
