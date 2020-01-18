"""Constants for the Garmin Connect integration."""
from datetime import timedelta

DOMAIN = "garmin_connect"
GARMIN_DEFAULT_CONDITIONS = ["totalSteps"]
ATTRIBUTION = "Data provided by garmin.com"
DEFAULT_NAME = "Garmin"
MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=10)

GARMIN_ENTITY_LIST = {
    "totalSteps": ["Total Steps", "steps", "mdi:walk"],
    "dailyStepGoal": ["Daily Step Goal", "steps", "mdi:walk"],
    "totalKilocalories": ["Total KiloCalories", "kcal", "mdi:food"],
    "activeKilocalories": ["Active KiloCalories", "kcal", "mdi:food"],
    "bmrKilocalories": ["BMR KiloCalories", "kcal", "mdi:food"],
    "consumedKilocalories": ["Consumed KiloCalories", "kcal", "mdi:food"],
    "burnedKilocalories": ["Burned KiloCalories", "kcal", "mdi:food"],
    "remainingKilocalories": ["Remaining KiloCalories", "kcal", "mdi:food"],
    "netRemainingKilocalories": ["Net Remaining KiloCalories", "kcal", "mdi:food"],
    "netCalorieGoal": ["Net Calorie Goal", "cal", "mdi:food"],
    "totalDistanceMeters": ["Total Distance Mtr", "mtr", "mdi:walk"],
    "wellnessStartTimeLocal": ["Wellness Start Time", "", "mdi:clock"],
    "wellnessEndTimeLocal": ["Wellness End Time", "", "mdi:clock"],
    "wellnessDescription": ["Wellness Description", "", "mdi:clock"],
    "wellnessDistanceMeters": ["Wellness Distance Mtr", "mtr", "mdi:walk"],
    "wellnessActiveKilocalories": ["Wellness Active KiloCalories", "kcal", "mdi:food"],
    "wellnessKilocalories": ["Wellness KiloCalories", "kcal", "mdi:food"],
    "highlyActiveSeconds": ["Highly Active Time", "minutes", "mdi:fire"],
    "activeSeconds": ["Active Time", "minutes", "mdi:fire"],
    "sedentarySeconds": ["Sedentary Time", "minutes", "mdi:seat"],
    "sleepingSeconds": ["Sleeping Time", "minutes", "mdi:sleep"],
    "measurableAwakeDuration": ["Awake Duration", "minutes", "mdi:sleep"],
    "measurableAsleepDuration": ["Sleep Duration", "minutes", "mdi:sleep"],
    "floorsAscendedInMeters": ["Floors Ascended Mtr", "mtr", "mdi:stairs"],
    "floorsDescendedInMeters": ["Floors Descended Mtr", "mtr", "mdi:stairs"],
    "floorsAscended": ["Floors Ascended", "floors", "mdi:stairs"],
    "floorsDescended": ["Floors Descended", "floors", "mdi:stairs"],
    "userFloorsAscendedGoal": ["Floors Ascended Goal", "", "mdi:stairs"],
    "minHeartRate": ["Min Heart Rate", "bpm", "mdi:heart-pulse"],
    "maxHeartRate": ["Max Heart Rate", "bpm", "mdi:heart-pulse"],
    "restingHeartRate": ["Resting Heart Rate", "bpm", "mdi:heart-pulse"],
    "minAvgHeartRate": ["Min Avg Heart Rate", "bpm", "mdi:heart-pulse"],
    "maxAvgHeartRate": ["Max Avg Heart Rate", "bpm", "mdi:heart-pulse"],
    "abnormalHeartRateAlertsCount": ["Abnormal HR Counts", "", "mdi:heart-pulse"],
    "lastSevenDaysAvgRestingHeartRate": [
        "Last 7 Days Avg Heart Rate",
        "bpm",
        "mdi:heart-pulse",
    ],
    "averageStressLevel": ["Avg Stress Level", "", "mdi:flash-alert"],
    "maxStressLevel": ["Max Stress Level", "", "mdi:flash-alert"],
    "stressQualifier": ["Stress Qualifier", "", "mdi:flash-alert"],
    "stressDuration": ["Stress Duration", "minutes", "mdi:flash-alert"],
    "restStressDuration": ["Rest Stress Duration", "minutes", "mdi:flash-alert"],
    "activityStressDuration": [
        "Activity Stress Duration",
        "minutes",
        "mdi:flash-alert",
    ],
    "uncategorizedStressDuration": [
        "Uncat. Stress Duration",
        "minutes",
        "mdi:flash-alert",
    ],
    "totalStressDuration": ["Total Stress Duration", "minutes", "mdi:flash-alert"],
    "lowStressDuration": ["Low Stress Duration", "minutes", "mdi:flash-alert"],
    "mediumStressDuration": ["Medium Stress Duration", "minutes", "mdi:flash-alert"],
    "highStressDuration": ["High Stress Duration", "minutes", "mdi:flash-alert"],
    "stressPercentage": ["Stress Percentage", "%", "mdi:flash-alert"],
    "restStressPercentage": ["Rest Stress Percentage", "%", "mdi:flash-alert"],
    "activityStressPercentage": ["Activity Stress Percentage", "%", "mdi:flash-alert"],
    "uncategorizedStressPercentage": [
        "Uncat. Stress Percentage",
        "%",
        "mdi:flash-alert",
    ],
    "lowStressPercentage": ["Low Stress Percentage", "%", "mdi:flash-alert"],
    "mediumStressPercentage": ["Medium Stress Percentage", "%", "mdi:flash-alert"],
    "highStressPercentage": ["High Stress Percentage", "%", "mdi:flash-alert"],
    "moderateIntensityMinutes": ["Moderate Intensity", "minutes", "mdi:flash-alert"],
    "vigorousIntensityMinutes": ["Vigorous Intensity", "minutes", "mdi:run-fast"],
    "intensityMinutesGoal": ["Intensity Goal", "minutes", "mdi:run-fast"],
    "bodyBatteryChargedValue": [
        "Body Battery Charged",
        "%",
        "mdi:battery-charging-100",
    ],
    "bodyBatteryDrainedValue": [
        "Body Battery Drained",
        "%",
        "mdi:battery-alert-variant-outline",
    ],
    "bodyBatteryHighestValue": ["Body Battery Highest", "%", "mdi:battery-heart"],
    "bodyBatteryLowestValue": ["Body Battery Lowest", "%", "mdi:battery-heart-outline"],
    "bodyBatteryMostRecentValue": [
        "Body Battery Most Recent",
        "%",
        "mdi:battery-positive",
    ],
    "averageSpo2": ["Average SPO2", "%", "mdi:diabetes"],
    "lowestSpo2": ["Lowest SPO2", "%", "mdi:diabetes"],
    "latestSpo2": ["Latest SPO2", "%", "mdi:diabetes"],
    "latestSpo2ReadingTimeLocal": ["Latest SPO2 Time", "", "mdi:diabetes"],
    "averageMonitoringEnvironmentAltitude": [
        "Average Altitude",
        "%",
        "mdi:image-filter-hdr",
    ],
    "highestRespirationValue": ["Highest Respiration", "brpm", "mdi:progress-clock"],
    "lowestRespirationValue": ["Lowest Respiration", "brpm", "mdi:progress-clock"],
    "latestRespirationValue": ["Latest Respiration", "brpm", "mdi:progress-clock"],
    "latestRespirationTimeGMT": ["Latest Respiration Update", "", "mdi:progress-clock"],
}
