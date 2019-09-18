"""Mock import ya_ma library for the tests."""
import sys
from unittest.mock import Mock

fake_module = Mock()

REPLY = {
    "data": {
        "geometries": [{"type": "Point", "coordinates": [37.565280044, 55.851959656]}],
        "geometry": {"type": "Point", "coordinates": [37.565280044, 55.851959656]},
        "properties": {
            "name": "7-й автобусный парк",
            "description": "7-й автобусный парк",
            "currentTime": "Mon Sep 16 2019 21:40:40 GMT+0300 (Moscow Standard Time)",
            "StopMetaData": {
                "id": "stop__9639579",
                "name": "7-й автобусный парк",
                "type": "urban",
                "region": {
                    "id": 213,
                    "type": 6,
                    "parent_id": 1,
                    "capital_id": 0,
                    "geo_parent_id": 0,
                    "city_id": 213,
                    "name": "moscow",
                    "native_name": "",
                    "iso_name": "RU MOW",
                    "is_main": True,
                    "en_name": "Moscow",
                    "short_en_name": "MSK",
                    "phone_code": "495 499",
                    "phone_code_old": "095",
                    "zip_code": "",
                    "population": 12506468,
                    "synonyms": "Moskau, Moskva",
                    "latitude": 55.753215,
                    "longitude": 37.622504,
                    "latitude_size": 0.878654,
                    "longitude_size": 1.164423,
                    "zoom": 10,
                    "tzname": "Europe/Moscow",
                    "official_languages": "ru",
                    "widespread_languages": "ru",
                    "suggest_list": [],
                    "is_eu": False,
                    "services_names": [
                        "bs",
                        "yaca",
                        "weather",
                        "afisha",
                        "maps",
                        "tv",
                        "ad",
                        "etrain",
                        "subway",
                        "delivery",
                        "route",
                    ],
                    "ename": "moscow",
                    "bounds": [
                        [37.0402925, 55.31141404514547],
                        [38.2047155, 56.190068045145466],
                    ],
                    "names": {
                        "ablative": "",
                        "accusative": "Москву",
                        "dative": "Москве",
                        "directional": "",
                        "genitive": "Москвы",
                        "instrumental": "Москвой",
                        "locative": "",
                        "nominative": "Москва",
                        "preposition": "в",
                        "prepositional": "Москве",
                    },
                    "parent": {
                        "id": 1,
                        "type": 5,
                        "parent_id": 3,
                        "capital_id": 213,
                        "geo_parent_id": 0,
                        "city_id": 213,
                        "name": "moscow-and-moscow-oblast",
                        "native_name": "",
                        "iso_name": "RU-MOS",
                        "is_main": True,
                        "en_name": "Moscow and Moscow Oblast",
                        "short_en_name": "RU-MOS",
                        "phone_code": "495 496 498 499",
                        "phone_code_old": "",
                        "zip_code": "",
                        "population": 7503385,
                        "synonyms": "Московская область, Подмосковье, Podmoskovye",
                        "latitude": 55.815792,
                        "longitude": 37.380031,
                        "latitude_size": 2.705659,
                        "longitude_size": 5.060749,
                        "zoom": 8,
                        "tzname": "Europe/Moscow",
                        "official_languages": "ru",
                        "widespread_languages": "ru",
                        "suggest_list": [
                            213,
                            10716,
                            10747,
                            10758,
                            20728,
                            10740,
                            10738,
                            20523,
                            10735,
                            10734,
                            10743,
                            21622,
                        ],
                        "is_eu": False,
                        "services_names": ["bs", "yaca", "ad"],
                        "ename": "moscow-and-moscow-oblast",
                        "bounds": [
                            [34.8496565, 54.439456064325434],
                            [39.9104055, 57.14511506432543],
                        ],
                        "names": {
                            "ablative": "",
                            "accusative": "Москву и Московскую область",
                            "dative": "Москве и Московской области",
                            "directional": "",
                            "genitive": "Москвы и Московской области",
                            "instrumental": "Москвой и Московской областью",
                            "locative": "",
                            "nominative": "Москва и Московская область",
                            "preposition": "в",
                            "prepositional": "Москве и Московской области",
                        },
                        "parent": {
                            "id": 225,
                            "type": 3,
                            "parent_id": 10001,
                            "capital_id": 213,
                            "geo_parent_id": 0,
                            "city_id": 213,
                            "name": "russia",
                            "native_name": "",
                            "iso_name": "RU",
                            "is_main": False,
                            "en_name": "Russia",
                            "short_en_name": "RU",
                            "phone_code": "7",
                            "phone_code_old": "",
                            "zip_code": "",
                            "population": 146880432,
                            "synonyms": "Russian Federation,Российская Федерация",
                            "latitude": 61.698653,
                            "longitude": 99.505405,
                            "latitude_size": 40.700127,
                            "longitude_size": 171.643239,
                            "zoom": 3,
                            "tzname": "",
                            "official_languages": "ru",
                            "widespread_languages": "ru",
                            "suggest_list": [
                                213,
                                2,
                                65,
                                54,
                                47,
                                43,
                                66,
                                51,
                                56,
                                172,
                                39,
                                62,
                            ],
                            "is_eu": False,
                            "services_names": ["bs", "yaca", "ad"],
                            "ename": "russia",
                            "bounds": [
                                [13.683785499999999, 35.290400699917846],
                                [-174.6729755, 75.99052769991785],
                            ],
                            "names": {
                                "ablative": "",
                                "accusative": "Россию",
                                "dative": "России",
                                "directional": "",
                                "genitive": "России",
                                "instrumental": "Россией",
                                "locative": "",
                                "nominative": "Россия",
                                "preposition": "в",
                                "prepositional": "России",
                            },
                        },
                    },
                },
                "Transport": [
                    {
                        "lineId": "2036925416",
                        "name": "194",
                        "Types": ["bus"],
                        "type": "bus",
                        "threads": [
                            {
                                "threadId": "2036927196",
                                "EssentialStops": [
                                    {
                                        "id": "stop__9711780",
                                        "name": "Метро Петровско-Разумовская",
                                    },
                                    {"id": "stop__9648742", "name": "Коровино"},
                                ],
                                "BriefSchedule": {
                                    "Events": [
                                        {
                                            "Scheduled": {
                                                "value": "1568659860",
                                                "tzOffset": 10800,
                                                "text": "21:51",
                                            }
                                        },
                                        {
                                            "Scheduled": {
                                                "value": "1568660760",
                                                "tzOffset": 10800,
                                                "text": "22:06",
                                            }
                                        },
                                        {
                                            "Scheduled": {
                                                "value": "1568661840",
                                                "tzOffset": 10800,
                                                "text": "22:24",
                                            }
                                        },
                                    ],
                                    "departureTime": "21:51",
                                },
                            }
                        ],
                        "threadId": "2036927196",
                        "EssentialStops": [
                            {
                                "id": "stop__9711780",
                                "name": "Метро Петровско-Разумовская",
                            },
                            {"id": "stop__9648742", "name": "Коровино"},
                        ],
                        "BriefSchedule": {
                            "Events": [
                                {
                                    "Scheduled": {
                                        "value": "1568659860",
                                        "tzOffset": 10800,
                                        "text": "21:51",
                                    }
                                },
                                {
                                    "Scheduled": {
                                        "value": "1568660760",
                                        "tzOffset": 10800,
                                        "text": "22:06",
                                    }
                                },
                                {
                                    "Scheduled": {
                                        "value": "1568661840",
                                        "tzOffset": 10800,
                                        "text": "22:24",
                                    }
                                },
                            ],
                            "departureTime": "21:51",
                        },
                    },
                    {
                        "lineId": "213_114_bus_mosgortrans",
                        "name": "114",
                        "Types": ["bus"],
                        "type": "bus",
                        "threads": [
                            {
                                "threadId": "213B_114_bus_mosgortrans",
                                "EssentialStops": [
                                    {"id": "stop__9647199", "name": "Метро Войковская"},
                                    {
                                        "id": "stop__9639588",
                                        "name": "Коровинское шоссе",
                                    },
                                ],
                                "BriefSchedule": {
                                    "Events": [],
                                    "Frequency": {
                                        "text": "15 мин",
                                        "value": 900,
                                        "begin": {
                                            "value": "1568603405",
                                            "tzOffset": 10800,
                                            "text": "6:10",
                                        },
                                        "end": {
                                            "value": "1568672165",
                                            "tzOffset": 10800,
                                            "text": "1:16",
                                        },
                                    },
                                },
                            }
                        ],
                        "threadId": "213B_114_bus_mosgortrans",
                        "EssentialStops": [
                            {"id": "stop__9647199", "name": "Метро Войковская"},
                            {"id": "stop__9639588", "name": "Коровинское шоссе"},
                        ],
                        "BriefSchedule": {
                            "Events": [],
                            "Frequency": {
                                "text": "15 мин",
                                "value": 900,
                                "begin": {
                                    "value": "1568603405",
                                    "tzOffset": 10800,
                                    "text": "6:10",
                                },
                                "end": {
                                    "value": "1568672165",
                                    "tzOffset": 10800,
                                    "text": "1:16",
                                },
                            },
                        },
                    },
                    {
                        "lineId": "213_154_bus_mosgortrans",
                        "name": "154",
                        "Types": ["bus"],
                        "type": "bus",
                        "threads": [
                            {
                                "threadId": "213B_154_bus_mosgortrans",
                                "EssentialStops": [
                                    {"id": "stop__9642548", "name": "ВДНХ (южная)"},
                                    {"id": "stop__9711744", "name": "Станция Ховрино"},
                                ],
                                "BriefSchedule": {
                                    "Events": [
                                        {
                                            "Scheduled": {
                                                "value": "1568659260",
                                                "tzOffset": 10800,
                                                "text": "21:41",
                                            },
                                            "Estimated": {
                                                "value": "1568659252",
                                                "tzOffset": 10800,
                                                "text": "21:40",
                                            },
                                            "vehicleId": "codd%5Fnew|1054764%5F191500",
                                        },
                                        {
                                            "Scheduled": {
                                                "value": "1568660580",
                                                "tzOffset": 10800,
                                                "text": "22:03",
                                            }
                                        },
                                        {
                                            "Scheduled": {
                                                "value": "1568661900",
                                                "tzOffset": 10800,
                                                "text": "22:25",
                                            }
                                        },
                                    ],
                                    "departureTime": "21:41",
                                },
                            }
                        ],
                        "threadId": "213B_154_bus_mosgortrans",
                        "EssentialStops": [
                            {"id": "stop__9642548", "name": "ВДНХ (южная)"},
                            {"id": "stop__9711744", "name": "Станция Ховрино"},
                        ],
                        "BriefSchedule": {
                            "Events": [
                                {
                                    "Scheduled": {
                                        "value": "1568659260",
                                        "tzOffset": 10800,
                                        "text": "21:41",
                                    },
                                    "Estimated": {
                                        "value": "1568659252",
                                        "tzOffset": 10800,
                                        "text": "21:40",
                                    },
                                    "vehicleId": "codd%5Fnew|1054764%5F191500",
                                },
                                {
                                    "Scheduled": {
                                        "value": "1568660580",
                                        "tzOffset": 10800,
                                        "text": "22:03",
                                    }
                                },
                                {
                                    "Scheduled": {
                                        "value": "1568661900",
                                        "tzOffset": 10800,
                                        "text": "22:25",
                                    }
                                },
                            ],
                            "departureTime": "21:41",
                        },
                    },
                    {
                        "lineId": "213_179_bus_mosgortrans",
                        "name": "179",
                        "Types": ["bus"],
                        "type": "bus",
                        "threads": [
                            {
                                "threadId": "213B_179_bus_mosgortrans",
                                "EssentialStops": [
                                    {"id": "stop__9647199", "name": "Метро Войковская"},
                                    {
                                        "id": "stop__9639480",
                                        "name": "Платформа Лианозово",
                                    },
                                ],
                                "BriefSchedule": {
                                    "Events": [
                                        {
                                            "Scheduled": {
                                                "value": "1568659920",
                                                "tzOffset": 10800,
                                                "text": "21:52",
                                            },
                                            "Estimated": {
                                                "value": "1568659351",
                                                "tzOffset": 10800,
                                                "text": "21:42",
                                            },
                                            "vehicleId": "codd%5Fnew|59832%5F31359",
                                        },
                                        {
                                            "Scheduled": {
                                                "value": "1568660760",
                                                "tzOffset": 10800,
                                                "text": "22:06",
                                            }
                                        },
                                        {
                                            "Scheduled": {
                                                "value": "1568661660",
                                                "tzOffset": 10800,
                                                "text": "22:21",
                                            }
                                        },
                                    ],
                                    "departureTime": "21:52",
                                },
                            }
                        ],
                        "threadId": "213B_179_bus_mosgortrans",
                        "EssentialStops": [
                            {"id": "stop__9647199", "name": "Метро Войковская"},
                            {"id": "stop__9639480", "name": "Платформа Лианозово"},
                        ],
                        "BriefSchedule": {
                            "Events": [
                                {
                                    "Scheduled": {
                                        "value": "1568659920",
                                        "tzOffset": 10800,
                                        "text": "21:52",
                                    },
                                    "Estimated": {
                                        "value": "1568659351",
                                        "tzOffset": 10800,
                                        "text": "21:42",
                                    },
                                    "vehicleId": "codd%5Fnew|59832%5F31359",
                                },
                                {
                                    "Scheduled": {
                                        "value": "1568660760",
                                        "tzOffset": 10800,
                                        "text": "22:06",
                                    }
                                },
                                {
                                    "Scheduled": {
                                        "value": "1568661660",
                                        "tzOffset": 10800,
                                        "text": "22:21",
                                    }
                                },
                            ],
                            "departureTime": "21:52",
                        },
                    },
                    {
                        "lineId": "213_191m_minibus_default",
                        "name": "591",
                        "Types": ["bus"],
                        "type": "bus",
                        "threads": [
                            {
                                "threadId": "213A_191m_minibus_default",
                                "EssentialStops": [
                                    {"id": "stop__9647199", "name": "Метро Войковская"},
                                    {"id": "stop__9711744", "name": "Станция Ховрино"},
                                ],
                                "BriefSchedule": {
                                    "Events": [
                                        {
                                            "Estimated": {
                                                "value": "1568660525",
                                                "tzOffset": 10800,
                                                "text": "22:02",
                                            },
                                            "vehicleId": "codd%5Fnew|38278%5F9345312",
                                        }
                                    ],
                                    "Frequency": {
                                        "text": "22 мин",
                                        "value": 1320,
                                        "begin": {
                                            "value": "1568602033",
                                            "tzOffset": 10800,
                                            "text": "5:47",
                                        },
                                        "end": {
                                            "value": "1568672233",
                                            "tzOffset": 10800,
                                            "text": "1:17",
                                        },
                                    },
                                },
                            }
                        ],
                        "threadId": "213A_191m_minibus_default",
                        "EssentialStops": [
                            {"id": "stop__9647199", "name": "Метро Войковская"},
                            {"id": "stop__9711744", "name": "Станция Ховрино"},
                        ],
                        "BriefSchedule": {
                            "Events": [
                                {
                                    "Estimated": {
                                        "value": "1568660525",
                                        "tzOffset": 10800,
                                        "text": "22:02",
                                    },
                                    "vehicleId": "codd%5Fnew|38278%5F9345312",
                                }
                            ],
                            "Frequency": {
                                "text": "22 мин",
                                "value": 1320,
                                "begin": {
                                    "value": "1568602033",
                                    "tzOffset": 10800,
                                    "text": "5:47",
                                },
                                "end": {
                                    "value": "1568672233",
                                    "tzOffset": 10800,
                                    "text": "1:17",
                                },
                            },
                        },
                    },
                    {
                        "lineId": "213_206m_minibus_default",
                        "name": "206к",
                        "Types": ["bus"],
                        "type": "bus",
                        "threads": [
                            {
                                "threadId": "213A_206m_minibus_default",
                                "EssentialStops": [
                                    {
                                        "id": "stop__9640756",
                                        "name": "Метро Петровско-Разумовская",
                                    },
                                    {"id": "stop__9640553", "name": "Лобненская улица"},
                                ],
                                "BriefSchedule": {
                                    "Events": [],
                                    "Frequency": {
                                        "text": "22 мин",
                                        "value": 1320,
                                        "begin": {
                                            "value": "1568601239",
                                            "tzOffset": 10800,
                                            "text": "5:33",
                                        },
                                        "end": {
                                            "value": "1568671439",
                                            "tzOffset": 10800,
                                            "text": "1:03",
                                        },
                                    },
                                },
                            }
                        ],
                        "threadId": "213A_206m_minibus_default",
                        "EssentialStops": [
                            {
                                "id": "stop__9640756",
                                "name": "Метро Петровско-Разумовская",
                            },
                            {"id": "stop__9640553", "name": "Лобненская улица"},
                        ],
                        "BriefSchedule": {
                            "Events": [],
                            "Frequency": {
                                "text": "22 мин",
                                "value": 1320,
                                "begin": {
                                    "value": "1568601239",
                                    "tzOffset": 10800,
                                    "text": "5:33",
                                },
                                "end": {
                                    "value": "1568671439",
                                    "tzOffset": 10800,
                                    "text": "1:03",
                                },
                            },
                        },
                    },
                    {
                        "lineId": "213_215_bus_mosgortrans",
                        "name": "215",
                        "Types": ["bus"],
                        "type": "bus",
                        "threads": [
                            {
                                "threadId": "213B_215_bus_mosgortrans",
                                "EssentialStops": [
                                    {
                                        "id": "stop__9711780",
                                        "name": "Метро Петровско-Разумовская",
                                    },
                                    {"id": "stop__9711744", "name": "Станция Ховрино"},
                                ],
                                "BriefSchedule": {
                                    "Events": [],
                                    "Frequency": {
                                        "text": "27 мин",
                                        "value": 1620,
                                        "begin": {
                                            "value": "1568601276",
                                            "tzOffset": 10800,
                                            "text": "5:34",
                                        },
                                        "end": {
                                            "value": "1568671476",
                                            "tzOffset": 10800,
                                            "text": "1:04",
                                        },
                                    },
                                },
                            }
                        ],
                        "threadId": "213B_215_bus_mosgortrans",
                        "EssentialStops": [
                            {
                                "id": "stop__9711780",
                                "name": "Метро Петровско-Разумовская",
                            },
                            {"id": "stop__9711744", "name": "Станция Ховрино"},
                        ],
                        "BriefSchedule": {
                            "Events": [],
                            "Frequency": {
                                "text": "27 мин",
                                "value": 1620,
                                "begin": {
                                    "value": "1568601276",
                                    "tzOffset": 10800,
                                    "text": "5:34",
                                },
                                "end": {
                                    "value": "1568671476",
                                    "tzOffset": 10800,
                                    "text": "1:04",
                                },
                            },
                        },
                    },
                    {
                        "lineId": "213_282_bus_mosgortrans",
                        "name": "282",
                        "Types": ["bus"],
                        "type": "bus",
                        "threads": [
                            {
                                "threadId": "213A_282_bus_mosgortrans",
                                "EssentialStops": [
                                    {"id": "stop__9641102", "name": "Улица Корнейчука"},
                                    {"id": "2532226085", "name": "Метро Войковская"},
                                ],
                                "BriefSchedule": {
                                    "Events": [
                                        {
                                            "Estimated": {
                                                "value": "1568659888",
                                                "tzOffset": 10800,
                                                "text": "21:51",
                                            },
                                            "vehicleId": "codd%5Fnew|34874%5F9345408",
                                        }
                                    ],
                                    "Frequency": {
                                        "text": "15 мин",
                                        "value": 900,
                                        "begin": {
                                            "value": "1568602180",
                                            "tzOffset": 10800,
                                            "text": "5:49",
                                        },
                                        "end": {
                                            "value": "1568673460",
                                            "tzOffset": 10800,
                                            "text": "1:37",
                                        },
                                    },
                                },
                            }
                        ],
                        "threadId": "213A_282_bus_mosgortrans",
                        "EssentialStops": [
                            {"id": "stop__9641102", "name": "Улица Корнейчука"},
                            {"id": "2532226085", "name": "Метро Войковская"},
                        ],
                        "BriefSchedule": {
                            "Events": [
                                {
                                    "Estimated": {
                                        "value": "1568659888",
                                        "tzOffset": 10800,
                                        "text": "21:51",
                                    },
                                    "vehicleId": "codd%5Fnew|34874%5F9345408",
                                }
                            ],
                            "Frequency": {
                                "text": "15 мин",
                                "value": 900,
                                "begin": {
                                    "value": "1568602180",
                                    "tzOffset": 10800,
                                    "text": "5:49",
                                },
                                "end": {
                                    "value": "1568673460",
                                    "tzOffset": 10800,
                                    "text": "1:37",
                                },
                            },
                        },
                    },
                    {
                        "lineId": "213_294m_minibus_default",
                        "name": "994",
                        "Types": ["bus"],
                        "type": "bus",
                        "threads": [
                            {
                                "threadId": "213A_294m_minibus_default",
                                "EssentialStops": [
                                    {
                                        "id": "stop__9640756",
                                        "name": "Метро Петровско-Разумовская",
                                    },
                                    {"id": "stop__9649459", "name": "Метро Алтуфьево"},
                                ],
                                "BriefSchedule": {
                                    "Events": [],
                                    "Frequency": {
                                        "text": "30 мин",
                                        "value": 1800,
                                        "begin": {
                                            "value": "1568601527",
                                            "tzOffset": 10800,
                                            "text": "5:38",
                                        },
                                        "end": {
                                            "value": "1568671727",
                                            "tzOffset": 10800,
                                            "text": "1:08",
                                        },
                                    },
                                },
                            }
                        ],
                        "threadId": "213A_294m_minibus_default",
                        "EssentialStops": [
                            {
                                "id": "stop__9640756",
                                "name": "Метро Петровско-Разумовская",
                            },
                            {"id": "stop__9649459", "name": "Метро Алтуфьево"},
                        ],
                        "BriefSchedule": {
                            "Events": [],
                            "Frequency": {
                                "text": "30 мин",
                                "value": 1800,
                                "begin": {
                                    "value": "1568601527",
                                    "tzOffset": 10800,
                                    "text": "5:38",
                                },
                                "end": {
                                    "value": "1568671727",
                                    "tzOffset": 10800,
                                    "text": "1:08",
                                },
                            },
                        },
                    },
                    {
                        "lineId": "213_36_trolleybus_mosgortrans",
                        "name": "т36",
                        "Types": ["bus"],
                        "type": "bus",
                        "threads": [
                            {
                                "threadId": "213A_36_trolleybus_mosgortrans",
                                "EssentialStops": [
                                    {"id": "stop__9642550", "name": "ВДНХ (южная)"},
                                    {
                                        "id": "stop__9640641",
                                        "name": "Дмитровское шоссе, 155",
                                    },
                                ],
                                "BriefSchedule": {
                                    "Events": [
                                        {
                                            "Scheduled": {
                                                "value": "1568659680",
                                                "tzOffset": 10800,
                                                "text": "21:48",
                                            },
                                            "Estimated": {
                                                "value": "1568659426",
                                                "tzOffset": 10800,
                                                "text": "21:43",
                                            },
                                            "vehicleId": "codd%5Fnew|1084829%5F430260",
                                        },
                                        {
                                            "Scheduled": {
                                                "value": "1568660520",
                                                "tzOffset": 10800,
                                                "text": "22:02",
                                            },
                                            "Estimated": {
                                                "value": "1568659656",
                                                "tzOffset": 10800,
                                                "text": "21:47",
                                            },
                                            "vehicleId": "codd%5Fnew|1117016%5F430280",
                                        },
                                        {
                                            "Scheduled": {
                                                "value": "1568661900",
                                                "tzOffset": 10800,
                                                "text": "22:25",
                                            },
                                            "Estimated": {
                                                "value": "1568660538",
                                                "tzOffset": 10800,
                                                "text": "22:02",
                                            },
                                            "vehicleId": "codd%5Fnew|1054576%5F430226",
                                        },
                                    ],
                                    "departureTime": "21:48",
                                },
                            }
                        ],
                        "threadId": "213A_36_trolleybus_mosgortrans",
                        "EssentialStops": [
                            {"id": "stop__9642550", "name": "ВДНХ (южная)"},
                            {"id": "stop__9640641", "name": "Дмитровское шоссе, 155"},
                        ],
                        "BriefSchedule": {
                            "Events": [
                                {
                                    "Scheduled": {
                                        "value": "1568659680",
                                        "tzOffset": 10800,
                                        "text": "21:48",
                                    },
                                    "Estimated": {
                                        "value": "1568659426",
                                        "tzOffset": 10800,
                                        "text": "21:43",
                                    },
                                    "vehicleId": "codd%5Fnew|1084829%5F430260",
                                },
                                {
                                    "Scheduled": {
                                        "value": "1568660520",
                                        "tzOffset": 10800,
                                        "text": "22:02",
                                    },
                                    "Estimated": {
                                        "value": "1568659656",
                                        "tzOffset": 10800,
                                        "text": "21:47",
                                    },
                                    "vehicleId": "codd%5Fnew|1117016%5F430280",
                                },
                                {
                                    "Scheduled": {
                                        "value": "1568661900",
                                        "tzOffset": 10800,
                                        "text": "22:25",
                                    },
                                    "Estimated": {
                                        "value": "1568660538",
                                        "tzOffset": 10800,
                                        "text": "22:02",
                                    },
                                    "vehicleId": "codd%5Fnew|1054576%5F430226",
                                },
                            ],
                            "departureTime": "21:48",
                        },
                    },
                    {
                        "lineId": "213_47_trolleybus_mosgortrans",
                        "name": "т47",
                        "Types": ["bus"],
                        "type": "bus",
                        "threads": [
                            {
                                "threadId": "213B_47_trolleybus_mosgortrans",
                                "EssentialStops": [
                                    {
                                        "id": "stop__9639568",
                                        "name": "Бескудниковский переулок",
                                    },
                                    {
                                        "id": "stop__9641903",
                                        "name": "Бескудниковский переулок",
                                    },
                                ],
                                "BriefSchedule": {
                                    "Events": [
                                        {
                                            "Scheduled": {
                                                "value": "1568659980",
                                                "tzOffset": 10800,
                                                "text": "21:53",
                                            },
                                            "Estimated": {
                                                "value": "1568659253",
                                                "tzOffset": 10800,
                                                "text": "21:40",
                                            },
                                            "vehicleId": "codd%5Fnew|1112219%5F430329",
                                        },
                                        {
                                            "Scheduled": {
                                                "value": "1568660940",
                                                "tzOffset": 10800,
                                                "text": "22:09",
                                            },
                                            "Estimated": {
                                                "value": "1568660519",
                                                "tzOffset": 10800,
                                                "text": "22:01",
                                            },
                                            "vehicleId": "codd%5Fnew|1139620%5F430382",
                                        },
                                        {
                                            "Scheduled": {
                                                "value": "1568663580",
                                                "tzOffset": 10800,
                                                "text": "22:53",
                                            }
                                        },
                                    ],
                                    "departureTime": "21:53",
                                },
                            }
                        ],
                        "threadId": "213B_47_trolleybus_mosgortrans",
                        "EssentialStops": [
                            {"id": "stop__9639568", "name": "Бескудниковский переулок"},
                            {"id": "stop__9641903", "name": "Бескудниковский переулок"},
                        ],
                        "BriefSchedule": {
                            "Events": [
                                {
                                    "Scheduled": {
                                        "value": "1568659980",
                                        "tzOffset": 10800,
                                        "text": "21:53",
                                    },
                                    "Estimated": {
                                        "value": "1568659253",
                                        "tzOffset": 10800,
                                        "text": "21:40",
                                    },
                                    "vehicleId": "codd%5Fnew|1112219%5F430329",
                                },
                                {
                                    "Scheduled": {
                                        "value": "1568660940",
                                        "tzOffset": 10800,
                                        "text": "22:09",
                                    },
                                    "Estimated": {
                                        "value": "1568660519",
                                        "tzOffset": 10800,
                                        "text": "22:01",
                                    },
                                    "vehicleId": "codd%5Fnew|1139620%5F430382",
                                },
                                {
                                    "Scheduled": {
                                        "value": "1568663580",
                                        "tzOffset": 10800,
                                        "text": "22:53",
                                    }
                                },
                            ],
                            "departureTime": "21:53",
                        },
                    },
                    {
                        "lineId": "213_56_trolleybus_mosgortrans",
                        "name": "т56",
                        "Types": ["bus"],
                        "type": "bus",
                        "threads": [
                            {
                                "threadId": "213A_56_trolleybus_mosgortrans",
                                "EssentialStops": [
                                    {
                                        "id": "stop__9639561",
                                        "name": "Коровинское шоссе",
                                    },
                                    {
                                        "id": "stop__9639588",
                                        "name": "Коровинское шоссе",
                                    },
                                ],
                                "BriefSchedule": {
                                    "Events": [
                                        {
                                            "Estimated": {
                                                "value": "1568660675",
                                                "tzOffset": 10800,
                                                "text": "22:04",
                                            },
                                            "vehicleId": "codd%5Fnew|146304%5F31207",
                                        }
                                    ],
                                    "Frequency": {
                                        "text": "8 мин",
                                        "value": 480,
                                        "begin": {
                                            "value": "1568606244",
                                            "tzOffset": 10800,
                                            "text": "6:57",
                                        },
                                        "end": {
                                            "value": "1568670144",
                                            "tzOffset": 10800,
                                            "text": "0:42",
                                        },
                                    },
                                },
                            }
                        ],
                        "threadId": "213A_56_trolleybus_mosgortrans",
                        "EssentialStops": [
                            {"id": "stop__9639561", "name": "Коровинское шоссе"},
                            {"id": "stop__9639588", "name": "Коровинское шоссе"},
                        ],
                        "BriefSchedule": {
                            "Events": [
                                {
                                    "Estimated": {
                                        "value": "1568660675",
                                        "tzOffset": 10800,
                                        "text": "22:04",
                                    },
                                    "vehicleId": "codd%5Fnew|146304%5F31207",
                                }
                            ],
                            "Frequency": {
                                "text": "8 мин",
                                "value": 480,
                                "begin": {
                                    "value": "1568606244",
                                    "tzOffset": 10800,
                                    "text": "6:57",
                                },
                                "end": {
                                    "value": "1568670144",
                                    "tzOffset": 10800,
                                    "text": "0:42",
                                },
                            },
                        },
                    },
                    {
                        "lineId": "213_63_bus_mosgortrans",
                        "name": "63",
                        "Types": ["bus"],
                        "type": "bus",
                        "threads": [
                            {
                                "threadId": "213A_63_bus_mosgortrans",
                                "EssentialStops": [
                                    {"id": "stop__9640554", "name": "Лобненская улица"},
                                    {"id": "stop__9640553", "name": "Лобненская улица"},
                                ],
                                "BriefSchedule": {
                                    "Events": [
                                        {
                                            "Estimated": {
                                                "value": "1568659369",
                                                "tzOffset": 10800,
                                                "text": "21:42",
                                            },
                                            "vehicleId": "codd%5Fnew|38921%5F9215306",
                                        },
                                        {
                                            "Estimated": {
                                                "value": "1568660136",
                                                "tzOffset": 10800,
                                                "text": "21:55",
                                            },
                                            "vehicleId": "codd%5Fnew|38918%5F9215303",
                                        },
                                    ],
                                    "Frequency": {
                                        "text": "17 мин",
                                        "value": 1020,
                                        "begin": {
                                            "value": "1568600987",
                                            "tzOffset": 10800,
                                            "text": "5:29",
                                        },
                                        "end": {
                                            "value": "1568670227",
                                            "tzOffset": 10800,
                                            "text": "0:43",
                                        },
                                    },
                                },
                            }
                        ],
                        "threadId": "213A_63_bus_mosgortrans",
                        "EssentialStops": [
                            {"id": "stop__9640554", "name": "Лобненская улица"},
                            {"id": "stop__9640553", "name": "Лобненская улица"},
                        ],
                        "BriefSchedule": {
                            "Events": [
                                {
                                    "Estimated": {
                                        "value": "1568659369",
                                        "tzOffset": 10800,
                                        "text": "21:42",
                                    },
                                    "vehicleId": "codd%5Fnew|38921%5F9215306",
                                },
                                {
                                    "Estimated": {
                                        "value": "1568660136",
                                        "tzOffset": 10800,
                                        "text": "21:55",
                                    },
                                    "vehicleId": "codd%5Fnew|38918%5F9215303",
                                },
                            ],
                            "Frequency": {
                                "text": "17 мин",
                                "value": 1020,
                                "begin": {
                                    "value": "1568600987",
                                    "tzOffset": 10800,
                                    "text": "5:29",
                                },
                                "end": {
                                    "value": "1568670227",
                                    "tzOffset": 10800,
                                    "text": "0:43",
                                },
                            },
                        },
                    },
                    {
                        "lineId": "213_677_bus_mosgortrans",
                        "name": "677",
                        "Types": ["bus"],
                        "type": "bus",
                        "threads": [
                            {
                                "threadId": "213B_677_bus_mosgortrans",
                                "EssentialStops": [
                                    {
                                        "id": "stop__9639495",
                                        "name": "Метро Петровско-Разумовская",
                                    },
                                    {
                                        "id": "stop__9639480",
                                        "name": "Платформа Лианозово",
                                    },
                                ],
                                "BriefSchedule": {
                                    "Events": [
                                        {
                                            "Estimated": {
                                                "value": "1568659369",
                                                "tzOffset": 10800,
                                                "text": "21:42",
                                            },
                                            "vehicleId": "codd%5Fnew|11731%5F31376",
                                        }
                                    ],
                                    "Frequency": {
                                        "text": "4 мин",
                                        "value": 240,
                                        "begin": {
                                            "value": "1568600940",
                                            "tzOffset": 10800,
                                            "text": "5:29",
                                        },
                                        "end": {
                                            "value": "1568672640",
                                            "tzOffset": 10800,
                                            "text": "1:24",
                                        },
                                    },
                                },
                            }
                        ],
                        "threadId": "213B_677_bus_mosgortrans",
                        "EssentialStops": [
                            {
                                "id": "stop__9639495",
                                "name": "Метро Петровско-Разумовская",
                            },
                            {"id": "stop__9639480", "name": "Платформа Лианозово"},
                        ],
                        "BriefSchedule": {
                            "Events": [
                                {
                                    "Estimated": {
                                        "value": "1568659369",
                                        "tzOffset": 10800,
                                        "text": "21:42",
                                    },
                                    "vehicleId": "codd%5Fnew|11731%5F31376",
                                }
                            ],
                            "Frequency": {
                                "text": "4 мин",
                                "value": 240,
                                "begin": {
                                    "value": "1568600940",
                                    "tzOffset": 10800,
                                    "text": "5:29",
                                },
                                "end": {
                                    "value": "1568672640",
                                    "tzOffset": 10800,
                                    "text": "1:24",
                                },
                            },
                        },
                    },
                    {
                        "lineId": "213_692_bus_mosgortrans",
                        "name": "692",
                        "Types": ["bus"],
                        "type": "bus",
                        "threads": [
                            {
                                "threadId": "2036928706",
                                "EssentialStops": [
                                    {"id": "3163417967", "name": "Платформа Дегунино"},
                                    {"id": "3163417967", "name": "Платформа Дегунино"},
                                ],
                                "BriefSchedule": {
                                    "Events": [
                                        {
                                            "Scheduled": {
                                                "value": "1568660280",
                                                "tzOffset": 10800,
                                                "text": "21:58",
                                            },
                                            "Estimated": {
                                                "value": "1568660255",
                                                "tzOffset": 10800,
                                                "text": "21:57",
                                            },
                                            "vehicleId": "codd%5Fnew|63029%5F31485",
                                        },
                                        {
                                            "Scheduled": {
                                                "value": "1568693340",
                                                "tzOffset": 10800,
                                                "text": "7:09",
                                            }
                                        },
                                        {
                                            "Scheduled": {
                                                "value": "1568696940",
                                                "tzOffset": 10800,
                                                "text": "8:09",
                                            }
                                        },
                                    ],
                                    "departureTime": "21:58",
                                },
                            }
                        ],
                        "threadId": "2036928706",
                        "EssentialStops": [
                            {"id": "3163417967", "name": "Платформа Дегунино"},
                            {"id": "3163417967", "name": "Платформа Дегунино"},
                        ],
                        "BriefSchedule": {
                            "Events": [
                                {
                                    "Scheduled": {
                                        "value": "1568660280",
                                        "tzOffset": 10800,
                                        "text": "21:58",
                                    },
                                    "Estimated": {
                                        "value": "1568660255",
                                        "tzOffset": 10800,
                                        "text": "21:57",
                                    },
                                    "vehicleId": "codd%5Fnew|63029%5F31485",
                                },
                                {
                                    "Scheduled": {
                                        "value": "1568693340",
                                        "tzOffset": 10800,
                                        "text": "7:09",
                                    }
                                },
                                {
                                    "Scheduled": {
                                        "value": "1568696940",
                                        "tzOffset": 10800,
                                        "text": "8:09",
                                    }
                                },
                            ],
                            "departureTime": "21:58",
                        },
                    },
                    {
                        "lineId": "213_78_trolleybus_mosgortrans",
                        "name": "т78",
                        "Types": ["bus"],
                        "type": "bus",
                        "threads": [
                            {
                                "threadId": "213A_78_trolleybus_mosgortrans",
                                "EssentialStops": [
                                    {
                                        "id": "stop__9887464",
                                        "name": "9-я Северная линия",
                                    },
                                    {
                                        "id": "stop__9887464",
                                        "name": "9-я Северная линия",
                                    },
                                ],
                                "BriefSchedule": {
                                    "Events": [
                                        {
                                            "Scheduled": {
                                                "value": "1568659620",
                                                "tzOffset": 10800,
                                                "text": "21:47",
                                            },
                                            "Estimated": {
                                                "value": "1568659898",
                                                "tzOffset": 10800,
                                                "text": "21:51",
                                            },
                                            "vehicleId": "codd%5Fnew|147522%5F31184",
                                        },
                                        {
                                            "Scheduled": {
                                                "value": "1568660760",
                                                "tzOffset": 10800,
                                                "text": "22:06",
                                            }
                                        },
                                        {
                                            "Scheduled": {
                                                "value": "1568661900",
                                                "tzOffset": 10800,
                                                "text": "22:25",
                                            }
                                        },
                                    ],
                                    "departureTime": "21:47",
                                },
                            }
                        ],
                        "threadId": "213A_78_trolleybus_mosgortrans",
                        "EssentialStops": [
                            {"id": "stop__9887464", "name": "9-я Северная линия"},
                            {"id": "stop__9887464", "name": "9-я Северная линия"},
                        ],
                        "BriefSchedule": {
                            "Events": [
                                {
                                    "Scheduled": {
                                        "value": "1568659620",
                                        "tzOffset": 10800,
                                        "text": "21:47",
                                    },
                                    "Estimated": {
                                        "value": "1568659898",
                                        "tzOffset": 10800,
                                        "text": "21:51",
                                    },
                                    "vehicleId": "codd%5Fnew|147522%5F31184",
                                },
                                {
                                    "Scheduled": {
                                        "value": "1568660760",
                                        "tzOffset": 10800,
                                        "text": "22:06",
                                    }
                                },
                                {
                                    "Scheduled": {
                                        "value": "1568661900",
                                        "tzOffset": 10800,
                                        "text": "22:25",
                                    }
                                },
                            ],
                            "departureTime": "21:47",
                        },
                    },
                    {
                        "lineId": "213_82_bus_mosgortrans",
                        "name": "82",
                        "Types": ["bus"],
                        "type": "bus",
                        "threads": [
                            {
                                "threadId": "2036925244",
                                "EssentialStops": [
                                    {
                                        "id": "2310890052",
                                        "name": "Метро Верхние Лихоборы",
                                    },
                                    {
                                        "id": "2310890052",
                                        "name": "Метро Верхние Лихоборы",
                                    },
                                ],
                                "BriefSchedule": {
                                    "Events": [
                                        {
                                            "Scheduled": {
                                                "value": "1568659680",
                                                "tzOffset": 10800,
                                                "text": "21:48",
                                            }
                                        },
                                        {
                                            "Scheduled": {
                                                "value": "1568661780",
                                                "tzOffset": 10800,
                                                "text": "22:23",
                                            }
                                        },
                                        {
                                            "Scheduled": {
                                                "value": "1568663760",
                                                "tzOffset": 10800,
                                                "text": "22:56",
                                            }
                                        },
                                    ],
                                    "departureTime": "21:48",
                                },
                            }
                        ],
                        "threadId": "2036925244",
                        "EssentialStops": [
                            {"id": "2310890052", "name": "Метро Верхние Лихоборы"},
                            {"id": "2310890052", "name": "Метро Верхние Лихоборы"},
                        ],
                        "BriefSchedule": {
                            "Events": [
                                {
                                    "Scheduled": {
                                        "value": "1568659680",
                                        "tzOffset": 10800,
                                        "text": "21:48",
                                    }
                                },
                                {
                                    "Scheduled": {
                                        "value": "1568661780",
                                        "tzOffset": 10800,
                                        "text": "22:23",
                                    }
                                },
                                {
                                    "Scheduled": {
                                        "value": "1568663760",
                                        "tzOffset": 10800,
                                        "text": "22:56",
                                    }
                                },
                            ],
                            "departureTime": "21:48",
                        },
                    },
                    {
                        "lineId": "2465131598",
                        "name": "179к",
                        "Types": ["bus"],
                        "type": "bus",
                        "threads": [
                            {
                                "threadId": "2465131758",
                                "EssentialStops": [
                                    {
                                        "id": "stop__9640244",
                                        "name": "Платформа Лианозово",
                                    },
                                    {
                                        "id": "stop__9639480",
                                        "name": "Платформа Лианозово",
                                    },
                                ],
                                "BriefSchedule": {
                                    "Events": [
                                        {
                                            "Scheduled": {
                                                "value": "1568659500",
                                                "tzOffset": 10800,
                                                "text": "21:45",
                                            }
                                        },
                                        {
                                            "Scheduled": {
                                                "value": "1568659980",
                                                "tzOffset": 10800,
                                                "text": "21:53",
                                            }
                                        },
                                        {
                                            "Scheduled": {
                                                "value": "1568660880",
                                                "tzOffset": 10800,
                                                "text": "22:08",
                                            }
                                        },
                                    ],
                                    "departureTime": "21:45",
                                },
                            }
                        ],
                        "threadId": "2465131758",
                        "EssentialStops": [
                            {"id": "stop__9640244", "name": "Платформа Лианозово"},
                            {"id": "stop__9639480", "name": "Платформа Лианозово"},
                        ],
                        "BriefSchedule": {
                            "Events": [
                                {
                                    "Scheduled": {
                                        "value": "1568659500",
                                        "tzOffset": 10800,
                                        "text": "21:45",
                                    }
                                },
                                {
                                    "Scheduled": {
                                        "value": "1568659980",
                                        "tzOffset": 10800,
                                        "text": "21:53",
                                    }
                                },
                                {
                                    "Scheduled": {
                                        "value": "1568660880",
                                        "tzOffset": 10800,
                                        "text": "22:08",
                                    }
                                },
                            ],
                            "departureTime": "21:45",
                        },
                    },
                    {
                        "lineId": "466_bus_default",
                        "name": "466",
                        "Types": ["bus"],
                        "type": "bus",
                        "threads": [
                            {
                                "threadId": "466B_bus_default",
                                "EssentialStops": [
                                    {
                                        "id": "stop__9640546",
                                        "name": "Станция Бескудниково",
                                    },
                                    {
                                        "id": "stop__9640545",
                                        "name": "Станция Бескудниково",
                                    },
                                ],
                                "BriefSchedule": {
                                    "Events": [],
                                    "Frequency": {
                                        "text": "22 мин",
                                        "value": 1320,
                                        "begin": {
                                            "value": "1568604647",
                                            "tzOffset": 10800,
                                            "text": "6:30",
                                        },
                                        "end": {
                                            "value": "1568675447",
                                            "tzOffset": 10800,
                                            "text": "2:10",
                                        },
                                    },
                                },
                            }
                        ],
                        "threadId": "466B_bus_default",
                        "EssentialStops": [
                            {"id": "stop__9640546", "name": "Станция Бескудниково"},
                            {"id": "stop__9640545", "name": "Станция Бескудниково"},
                        ],
                        "BriefSchedule": {
                            "Events": [],
                            "Frequency": {
                                "text": "22 мин",
                                "value": 1320,
                                "begin": {
                                    "value": "1568604647",
                                    "tzOffset": 10800,
                                    "text": "6:30",
                                },
                                "end": {
                                    "value": "1568675447",
                                    "tzOffset": 10800,
                                    "text": "2:10",
                                },
                            },
                        },
                    },
                    {
                        "lineId": "677k_bus_default",
                        "name": "677к",
                        "Types": ["bus"],
                        "type": "bus",
                        "threads": [
                            {
                                "threadId": "677kA_bus_default",
                                "EssentialStops": [
                                    {
                                        "id": "stop__9640244",
                                        "name": "Платформа Лианозово",
                                    },
                                    {
                                        "id": "stop__9639480",
                                        "name": "Платформа Лианозово",
                                    },
                                ],
                                "BriefSchedule": {
                                    "Events": [
                                        {
                                            "Scheduled": {
                                                "value": "1568659920",
                                                "tzOffset": 10800,
                                                "text": "21:52",
                                            },
                                            "Estimated": {
                                                "value": "1568660003",
                                                "tzOffset": 10800,
                                                "text": "21:53",
                                            },
                                            "vehicleId": "codd%5Fnew|130308%5F31319",
                                        },
                                        {
                                            "Scheduled": {
                                                "value": "1568661240",
                                                "tzOffset": 10800,
                                                "text": "22:14",
                                            }
                                        },
                                        {
                                            "Scheduled": {
                                                "value": "1568662500",
                                                "tzOffset": 10800,
                                                "text": "22:35",
                                            }
                                        },
                                    ],
                                    "departureTime": "21:52",
                                },
                            }
                        ],
                        "threadId": "677kA_bus_default",
                        "EssentialStops": [
                            {"id": "stop__9640244", "name": "Платформа Лианозово"},
                            {"id": "stop__9639480", "name": "Платформа Лианозово"},
                        ],
                        "BriefSchedule": {
                            "Events": [
                                {
                                    "Scheduled": {
                                        "value": "1568659920",
                                        "tzOffset": 10800,
                                        "text": "21:52",
                                    },
                                    "Estimated": {
                                        "value": "1568660003",
                                        "tzOffset": 10800,
                                        "text": "21:53",
                                    },
                                    "vehicleId": "codd%5Fnew|130308%5F31319",
                                },
                                {
                                    "Scheduled": {
                                        "value": "1568661240",
                                        "tzOffset": 10800,
                                        "text": "22:14",
                                    }
                                },
                                {
                                    "Scheduled": {
                                        "value": "1568662500",
                                        "tzOffset": 10800,
                                        "text": "22:35",
                                    }
                                },
                            ],
                            "departureTime": "21:52",
                        },
                    },
                    {
                        "lineId": "m10_bus_default",
                        "name": "м10",
                        "Types": ["bus"],
                        "type": "bus",
                        "threads": [
                            {
                                "threadId": "2036926048",
                                "EssentialStops": [
                                    {"id": "stop__9640554", "name": "Лобненская улица"},
                                    {"id": "stop__9640553", "name": "Лобненская улица"},
                                ],
                                "BriefSchedule": {
                                    "Events": [
                                        {
                                            "Estimated": {
                                                "value": "1568659718",
                                                "tzOffset": 10800,
                                                "text": "21:48",
                                            },
                                            "vehicleId": "codd%5Fnew|146260%5F31212",
                                        },
                                        {
                                            "Estimated": {
                                                "value": "1568660422",
                                                "tzOffset": 10800,
                                                "text": "22:00",
                                            },
                                            "vehicleId": "codd%5Fnew|13997%5F31247",
                                        },
                                    ],
                                    "Frequency": {
                                        "text": "15 мин",
                                        "value": 900,
                                        "begin": {
                                            "value": "1568606903",
                                            "tzOffset": 10800,
                                            "text": "7:08",
                                        },
                                        "end": {
                                            "value": "1568675183",
                                            "tzOffset": 10800,
                                            "text": "2:06",
                                        },
                                    },
                                },
                            }
                        ],
                        "threadId": "2036926048",
                        "EssentialStops": [
                            {"id": "stop__9640554", "name": "Лобненская улица"},
                            {"id": "stop__9640553", "name": "Лобненская улица"},
                        ],
                        "BriefSchedule": {
                            "Events": [
                                {
                                    "Estimated": {
                                        "value": "1568659718",
                                        "tzOffset": 10800,
                                        "text": "21:48",
                                    },
                                    "vehicleId": "codd%5Fnew|146260%5F31212",
                                },
                                {
                                    "Estimated": {
                                        "value": "1568660422",
                                        "tzOffset": 10800,
                                        "text": "22:00",
                                    },
                                    "vehicleId": "codd%5Fnew|13997%5F31247",
                                },
                            ],
                            "Frequency": {
                                "text": "15 мин",
                                "value": 900,
                                "begin": {
                                    "value": "1568606903",
                                    "tzOffset": 10800,
                                    "text": "7:08",
                                },
                                "end": {
                                    "value": "1568675183",
                                    "tzOffset": 10800,
                                    "text": "2:06",
                                },
                            },
                        },
                    },
                ],
            },
        },
        "toponymSeoname": "dmitrovskoye_shosse",
    }
}


class MockRequester(object):
    """Fake YandexRequester object."""

    def __init__(self, user_agent=None):
        """Create mock module object, for avoid importing ya_ma library."""
        pass

    def get_stop_info(self, stop_id):
        """Fake method. Return information about stop_id 9639579."""
        return REPLY

    def set_new_session(self):
        """Fake method for reset http session."""
        pass


requester = MockRequester()
fake_module.YandexMapsRequester = MockRequester
sys.modules["ya_ma"] = fake_module
