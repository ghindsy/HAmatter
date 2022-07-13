"""Test SimpliSafe diagnostics."""
from homeassistant.components.diagnostics import REDACTED

from tests.components.diagnostics import get_diagnostics_for_config_entry


async def test_entry_diagnostics(hass, config_entry, hass_client, setup_simplisafe):
    """Test config entry diagnostics."""
    assert await get_diagnostics_for_config_entry(hass, hass_client, config_entry) == {
        "entry": {
            "options": {
                "code": REDACTED,
            },
        },
        "subscription_data": {
            "system_123": {
                "uid": REDACTED,
                "sid": REDACTED,
                "sStatus": 20,
                "activated": 1445034752,
                "planSku": "SSEDSM2",
                "planName": "Interactive Monitoring",
                "price": 24.99,
                "currency": "USD",
                "country": "US",
                "expires": REDACTED,
                "canceled": 0,
                "extraTime": 0,
                "creditCard": REDACTED,
                "time": 2628000,
                "paymentProfileId": REDACTED,
                "features": {
                    "monitoring": True,
                    "alerts": True,
                    "online": True,
                    "hazard": True,
                    "video": True,
                    "cameras": 10,
                    "dispatch": True,
                    "proInstall": False,
                    "discount": 0,
                    "vipCS": False,
                    "medical": True,
                    "careVisit": False,
                    "storageDays": 30,
                },
                "status": {
                    "hasBaseStation": True,
                    "isActive": True,
                    "monitoring": "Active",
                },
                "subscriptionFeatures": {
                    "monitoredSensorsTypes": [
                        "Entry",
                        "Motion",
                        "GlassBreak",
                        "Smoke",
                        "CO",
                        "Freeze",
                        "Water",
                    ],
                    "monitoredPanicConditions": ["Fire", "Medical", "Duress"],
                    "dispatchTypes": ["Police", "Fire", "Medical", "Guard"],
                    "remoteControl": [
                        "ArmDisarm",
                        "LockUnlock",
                        "ViewSettings",
                        "ConfigureSettings",
                    ],
                    "cameraFeatures": {
                        "liveView": True,
                        "maxRecordingCameras": 10,
                        "recordingStorageDays": 30,
                        "videoVerification": True,
                    },
                    "support": {
                        "level": "Basic",
                        "annualVisit": False,
                        "professionalInstall": False,
                    },
                    "cellCommunicationBackup": True,
                    "alertChannels": ["Push", "SMS", "Email"],
                    "alertTypes": ["Alarm", "Error", "Activity", "Camera"],
                    "alarmModes": ["Alarm", "SecretAlert", "Disabled"],
                    "supportedIntegrations": [
                        "GoogleAssistant",
                        "AmazonAlexa",
                        "AugustLock",
                    ],
                    "timeline": {},
                },
                "dispatcher": "cops",
                "dcid": 0,
                "location": REDACTED,
                "pinUnlocked": True,
                "billDate": 1602887552,
                "billInterval": 2628000,
                "pinUnlockedBy": "pin",
                "autoActivation": None,
            }
        },
        "systems": [
            {
                "address": REDACTED,
                "alarm_going_off": False,
                "connection_type": "wifi",
                "notifications": [],
                "serial": REDACTED,
                "state": 99,
                "system_id": REDACTED,
                "temperature": 67,
                "version": 3,
                "sensors": [
                    {
                        "name": "Fire Door",
                        "serial": REDACTED,
                        "type": 5,
                        "error": False,
                        "low_battery": False,
                        "offline": False,
                        "settings": {
                            "instantTrigger": False,
                            "away2": 1,
                            "away": 1,
                            "home2": 1,
                            "home": 1,
                            "off": 0,
                        },
                        "trigger_instantly": False,
                        "triggered": False,
                    },
                    {
                        "name": "Front Door",
                        "serial": REDACTED,
                        "type": 12,
                        "error": False,
                        "low_battery": False,
                        "offline": False,
                        "settings": {
                            "instantTrigger": False,
                            "away2": 1,
                            "away": 1,
                            "home2": 1,
                            "home": 1,
                            "off": 0,
                        },
                        "trigger_instantly": False,
                        "triggered": False,
                    },
                ],
                "alarm_duration": 240,
                "alarm_volume": 3,
                "battery_backup_power_level": 5293,
                "cameras": [
                    {
                        "camera_settings": {
                            "cameraName": "Camera",
                            "pictureQuality": "720p",
                            "nightVision": "auto",
                            "statusLight": "off",
                            "micSensitivity": 100,
                            "micEnable": True,
                            "speakerVolume": 75,
                            "motionSensitivity": 0,
                            "shutterHome": "closedAlarmOnly",
                            "shutterAway": "open",
                            "shutterOff": "closedAlarmOnly",
                            "wifiSsid": "",
                            "canStream": False,
                            "canRecord": False,
                            "pirEnable": True,
                            "vaEnable": True,
                            "notificationsEnable": False,
                            "enableDoorbellNotification": True,
                            "doorbellChimeVolume": "off",
                            "privacyEnable": False,
                            "hdr": False,
                            "vaZoningEnable": False,
                            "vaZoningRows": 0,
                            "vaZoningCols": 0,
                            "vaZoningMask": [],
                            "maxDigitalZoom": 10,
                            "supportedResolutions": ["480p", "720p"],
                            "admin": {
                                "IRLED": 0,
                                "pirSens": 0,
                                "statusLEDState": 1,
                                "lux": "lowLux",
                                "motionDetectionEnabled": False,
                                "motionThresholdZero": 0,
                                "motionThresholdOne": 10000,
                                "levelChangeDelayZero": 30,
                                "levelChangeDelayOne": 10,
                                "audioDetectionEnabled": False,
                                "audioChannelNum": 2,
                                "audioSampleRate": 16000,
                                "audioChunkBytes": 2048,
                                "audioSampleFormat": 3,
                                "audioSensitivity": 50,
                                "audioThreshold": 50,
                                "audioDirection": 0,
                                "bitRate": 284,
                                "longPress": 2000,
                                "kframe": 1,
                                "gopLength": 40,
                                "idr": 1,
                                "fps": 20,
                                "firmwareVersion": "2.6.1.107",
                                "netConfigVersion": "",
                                "camAgentVersion": "",
                                "lastLogin": 1600639997,
                                "lastLogout": 1600639944,
                                "pirSampleRateMs": 800,
                                "pirHysteresisHigh": 2,
                                "pirHysteresisLow": 10,
                                "pirFilterCoefficient": 1,
                                "logEnabled": True,
                                "logLevel": 3,
                                "logQDepth": 20,
                                "firmwareGroup": "public",
                                "irOpenThreshold": 445,
                                "irCloseThreshold": 840,
                                "irOpenDelay": 3,
                                "irCloseDelay": 3,
                                "irThreshold1x": 388,
                                "irThreshold2x": 335,
                                "irThreshold3x": 260,
                                "rssi": [[1600935204, -43]],
                                "battery": [],
                                "dbm": 0,
                                "vmUse": 161592,
                                "resSet": 10540,
                                "uptime": 810043.74,
                                "wifiDisconnects": 1,
                                "wifiDriverReloads": 1,
                                "statsPeriod": 3600000,
                                "sarlaccDebugLogTypes": 0,
                                "odProcessingFps": 8,
                                "odObjectMinWidthPercent": 6,
                                "odObjectMinHeightPercent": 24,
                                "odEnableObjectDetection": True,
                                "odClassificationMask": 2,
                                "odClassificationConfidenceThreshold": 0.95,
                                "odEnableOverlay": False,
                                "odAnalyticsLib": 2,
                                "odSensitivity": 85,
                                "odEventObjectMask": 2,
                                "odLuxThreshold": 445,
                                "odLuxHysteresisHigh": 4,
                                "odLuxHysteresisLow": 4,
                                "odLuxSamplingFrequency": 30,
                                "odFGExtractorMode": 2,
                                "odVideoScaleFactor": 1,
                                "odSceneType": 1,
                                "odCameraView": 3,
                                "odCameraFOV": 2,
                                "odBackgroundLearnStationary": True,
                                "odBackgroundLearnStationarySpeed": 15,
                                "odClassifierQualityProfile": 1,
                                "odEnableVideoAnalyticsWhileStreaming": False,
                                "wlanMac": "XX:XX:XX:XX:XX:XX",
                                "region": "us-east-1",
                                "enableWifiAnalyticsLib": False,
                                "ivLicense": "",
                            },
                            "pirLevel": "medium",
                            "odLevel": "medium",
                        },
                        "camera_type": 0,
                        "name": "Camera",
                        "serial": REDACTED,
                        "shutter_open_when_away": True,
                        "shutter_open_when_home": False,
                        "shutter_open_when_off": False,
                        "status": "online",
                        "subscription_enabled": True,
                    }
                ],
                "chime_volume": 2,
                "entry_delay_away": 30,
                "entry_delay_home": 30,
                "exit_delay_away": 60,
                "exit_delay_home": 0,
                "gsm_strength": -73,
                "light": True,
                "locks": [
                    {
                        "name": "Front Door",
                        "serial": REDACTED,
                        "type": 16,
                        "error": False,
                        "low_battery": False,
                        "offline": False,
                        "settings": {
                            "autoLock": 3,
                            "away": 1,
                            "home": 1,
                            "awayToOff": 0,
                            "homeToOff": 1,
                        },
                        "disabled": False,
                        "lock_low_battery": False,
                        "pin_pad_low_battery": False,
                        "pin_pad_offline": False,
                        "state": 1,
                    }
                ],
                "offline": False,
                "power_outage": False,
                "rf_jamming": False,
                "voice_prompt_volume": 2,
                "wall_power_level": 5933,
                "wifi_ssid": REDACTED,
                "wifi_strength": -49,
            }
        ],
    }
