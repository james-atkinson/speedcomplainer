# speedcomplainer
A python app that will test your internet connection and then complain to your service provider (and log to a data store if you'd like). Note: This app will only work on python 2.7.13

## Configuration
Configuration is handled by a basic JSON file. Things that can be configured are:
* twitter
 * twitterToken: This is your app access token
 * twitterConsumerKey: This is your Consumer Key (API Key)
 * twitterTokenSecret: This is your Access Token Secret
 * TwitterConsumerSecret: This is your Consumer Secret (API Secret)
* tweetTo: This is a account (or list of accounts) that will be @ mentioned (include the @!)
* internetSpeed: This is the speed (in MB/sec) you're paying for (and presumably not getting).
* tweetThresholds: This is a list of messages that will be tweeted when you hit a threshold of crappiness. Placeholders are:
 * {tweetTo} - The above tweetTo configuration.
 * {internetSpeed} - The above internetSpeed configuration.
 * {downloadResult} - The poor download speed you're getting

Threshold Example (remember to limit your messages to 140 characters or less!):
```
    "tweetThresholds": {
        "5": [
            "Hey {tweetTo} I'm paying for {internetSpeed}Mb/s but getting only {downloadResult} Mb/s?!? Shame.",
            "Oi! {tweetTo} $100+/month for {internetSpeed}Mbit/s and I only get {downloadResult} Mbit/s? How does that seem fair?"
        ],
        "12.5": [
            "Uhh {tweetTo} for $100+/month I expect better than {downloadResult}Mbit/s when I'm paying for {internetSpeed}Mbit/s. Fix your network!",
            "Hey {tweetTo} why am I only getting {downloadResult}Mb/s when I pay for {internetSpeed}Mb/s? $100+/month for this??"
        ],
        "25": [
            "Well {tweetTo} I guess {downloadResult}Mb/s is better than nothing, still not worth $100/mnth when I expect {internetSpeed}Mb/s"
        ]
    }
```

Logging can be done to CSV files, with a log file for ping results and speed test results. 

CSV Logging config example:
```
"log": {
    "type": "csv",
    "files": {
        "ping": "pingresults.csv",
        "speed": "speedrestuls.csv"
    }
}
```

## Usage
> python speedcomplainer.py

Or to run in the background:

> python speedcomplainer.py > /dev/null &


