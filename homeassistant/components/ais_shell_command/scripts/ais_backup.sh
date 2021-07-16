# AIS dom backup script to create bootstrap
# last change 2021/07/05 by AR
ais_pro=$(su -c cat /system/build.prop | grep 'ro.product.name=AIS-PRO1' | wc -l)
if [ $ais_pro -gt 0 ]; then
  echo "OK, let use 6 CPUs"
else
  echo "We will use 2 CPUs"
fi

# 0. remove the gate ID
rm /data/data/pl.sviete.dom/files/home/AIS/.dom/.ais_secure_android_id_dom

# 1. clean cache files
apt-get autoremove --purge
apt-get clean
rm -rf ~/.cache/pip/*

# 2. stop HA and flush pm2 logs
pm2 delete tunnel
pm2 delete ssh-tunnel
pm2 delete zigbee
pm2 delete zwave
pm2 save
pm2 stop ais
pm2 flush

# 3. delete all the authentication data from HA
rm /data/data/pl.sviete.dom/files/home/AIS/.storage/auth
rm /data/data/pl.sviete.dom/files/home/AIS/.storage/auth_provider.homeassistant
rm /data/data/pl.sviete.dom/files/home/AIS/.storage/onboarding

# 4. delete all the devices from HA registry
rm /data/data/pl.sviete.dom/files/home/AIS/.storage/core.config_entries
rm /data/data/pl.sviete.dom/files/home/AIS/.storage/core.device_registry
rm /data/data/pl.sviete.dom/files/home/AIS/.storage/core.entity_registry
rm /data/data/pl.sviete.dom/files/home/AIS/.storage/core.restore_state
rm /data/data/pl.sviete.dom/files/home/AIS/.storage/core.area_registry
rm /data/data/pl.sviete.dom/files/home/AIS/.storage/core.config
rm /data/data/pl.sviete.dom/files/home/AIS/.storage/person


# 5. clear .dom folder - remove tokens and bookmarks
# logs and db settings
echo [] > ~/../myConnHist.json
rm -rf /data/data/pl.sviete.dom/files/home/AIS/.dom/.ais*
# create db settings for pro
if [ $ais_pro -gt 0 ]; then
  echo '{ "dbShowLogbook": true, "dbShowHistory": true, "dbEngine": "MariaDB (local)", "dbDrive": "", "dbUrl": "mysql+pymysql://ais:dom@127.0.0.1/ha?charset=utf8mb4", "dbPassword": "dom", "dbUser": "ais", "dbServerIp": "127.0.0.1", "dbServerName": "ha", "dbKeepDays": "10", "errorInfo": ""}' >  /data/data/pl.sviete.dom/files/home/AIS/.dom/.ais_db_settings_info
fi
# 6. clear npm cache
rm -rf /data/data/pl.sviete.dom/files/home/.npm/_cacache/*

# 7. delete all HA logs and DBs
rm /data/data/pl.sviete.dom/files/home/AIS/*.log
rm /data/data/pl.sviete.dom/files/home/AIS/*.db
rm /data/data/pl.sviete.dom/files/home/AIS/dom_access_code.png
rm /data/data/pl.sviete.dom/files/home/AIS/www/upgrade_log.txt
rm /data/data/pl.sviete.dom/files/home/AIS/www/id_rsa_ais
rm /data/data/pl.sviete.dom/files/home/AIS/www/*.png
rm /data/data/pl.sviete.dom/files/home/AIS/www/*.jpeg
rm -rf /data/data/pl.sviete.dom/files/usr/tmp/*

# 8. rclone
echo > /data/data/pl.sviete.dom/files/home/AIS/.dom/rclone.conf

# 9. Spotify
rm /data/data/pl.sviete.dom/files/home/AIS/.dom/.ais-dom-spotify-token-cache

# 10. change owner to current user for all files
su -c "chown -R $(id -u):$(id -g) /data/data/pl.sviete.dom/files"

# 11. delete zigbee config
rm /data/data/pl.sviete.dom/files/home/zigbee2mqtt/data/database.db
rm /data/data/pl.sviete.dom/files/home/zigbee2mqtt/data/state.json
echo "homeassistant: true" > /data/data/pl.sviete.dom/files/home/zigbee2mqtt/data/configuration.yaml
echo "permit_join: false" >> /data/data/pl.sviete.dom/files/home/zigbee2mqtt/data/configuration.yaml
echo "mqtt:" >> /data/data/pl.sviete.dom/files/home/zigbee2mqtt/data/configuration.yaml
echo "  base_topic: zigbee2mqtt" >> /data/data/pl.sviete.dom/files/home/zigbee2mqtt/data/configuration.yaml
echo "  server: 'mqtt://localhost'" >> /data/data/pl.sviete.dom/files/home/zigbee2mqtt/data/configuration.yaml
echo "serial:" >> /data/data/pl.sviete.dom/files/home/zigbee2mqtt/data/configuration.yaml
echo "  port: /dev/ttyACM0" >> /data/data/pl.sviete.dom/files/home/zigbee2mqtt/data/configuration.yaml
echo "  adapter: null" >> /data/data/pl.sviete.dom/files/home/zigbee2mqtt/data/configuration.yaml
echo "frontend:" >> /data/data/pl.sviete.dom/files/home/zigbee2mqtt/data/configuration.yaml
echo "  port: 8099" >> /data/data/pl.sviete.dom/files/home/zigbee2mqtt/data/configuration.yaml
echo "advanced:" >> /data/data/pl.sviete.dom/files/home/zigbee2mqtt/data/configuration.yaml
echo "  log_level: info" >> /data/data/pl.sviete.dom/files/home/zigbee2mqtt/data/configuration.yaml
echo "  log_output:" >> /data/data/pl.sviete.dom/files/home/zigbee2mqtt/data/configuration.yaml
echo "    - console" >> /data/data/pl.sviete.dom/files/home/zigbee2mqtt/data/configuration.yaml
echo "  channel: 11" >> /data/data/pl.sviete.dom/files/home/zigbee2mqtt/data/configuration.yaml

# 12. delete img galery
rm -rf /data/data/pl.sviete.dom/files/home/AIS/www/img/*

# 13. backup old bootstrap
mv /sdcard/files.tar.7z /sdcard/files.tar.7z.old


# 14. rm links to drives
rm -rf /data/data/pl.sviete.dom/files/home/dom/dyski-wymienne/*
rm -rf /data/data/pl.sviete.dom/files/home/dom/dyski-zewnętrzne/*
rm -rf /data/data/pl.sviete.dom/files/home/dom/dyski-zdalne/*

# 15. rm temps
rm -rf /data/data/pl.sviete.dom/files/home/dom/.temp
rm -rf /data/data/pl.sviete.dom/files/usr/tmp/*

# 16. rm the ais_setup_wizard_done file
rm /data/data/pl.sviete.dom/files/ais_setup_wizard_done

if [ $ais_pro -gt 0 ]; then
  # 17. clean DB
  # # drop database ha
  mysql -h 127.0.0.1 -u $(whoami) --execute="DROP DATABASE ha"
  # # create database ha
  mysql -h 127.0.0.1 -u $(whoami) --execute="CREATE DATABASE ha CHARACTER SET utf8;"
  # mysql -u $(whoami) --execute="CREATE USER 'ais'@'localhost' IDENTIFIED  BY 'dom';"
  mysql -h 127.0.0.1 -u $(whoami) --execute="GRANT ALL PRIVILEGES ON ha.* TO 'ais'@'localhost';"
  # test
  mysql -h 127.0.0.1 -u ais -pdom ha --execute="select 'DB TEST OK' as ais from dual;"
fi

# ON THE END -> create new bootstrap
cd /data/data/pl.sviete.dom
# su -c "tar -cvzf /sdcard/files.tar files"

if [ $ais_pro -gt 0 ]; then
  7za a -m0=lzma2 /sdcard/files.tar.7z /data/data/pl.sviete.dom/files
else
  # to prevent the kill form Android, 7z have to be limited to 2 threads only (mmt=2)
  7za a -m0=lzma2 /sdcard/files.tar.7z /data/data/pl.sviete.dom/files -mmt=2
fi

