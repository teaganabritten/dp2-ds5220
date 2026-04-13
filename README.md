# dp2-ds5220: Observing New York MTA Events Data

## Data and Project Description

This project pulls data from the MTA API, specifically events of the rail system in New York City. I chose the endpoint of the API subsetted to the 1, 2, 3, 4, 5, 6, and 7 trains and the Times Square-Grand Central shuttle. For this specific endpoint of the API, there are four possible values returned including information on the number of trains in service and any service alerts. The data for this dataset was pulled over the course of five days, from Wednesday (4/8/2026) to Sunday (4/12/2026) with the final 72 hours being displayed in the plot. The data collected is stored in JSON format, as pulled from the API. I chose this data source because the NYC Subway is of interest to me and its 24-hour service pattern allows for constant updates as to how the system is running, no matter the time. 

## Process Description 

The data is collected from the API on a constant schedule, polling the API every fifteen minutes. The cronjob would add the data upon collection to the DynamoDB table. That data would then be appended to the latest.json file and used to create a new graph. The new graph image then replaces the previous image to display only the most current graph to the website. I did not need to use Kubernetes secrets for an API key because the endpoint of the API that I accessed does not require one. Access to AWS tools was done using IAM role that gave permission for actions in DynamoDB and s3, allowing to add the data to the database, complete the necessary tasks of making the graph and updating the datafile, and then writing that to s3. 

## Graph Description

The graph plots the last 72 hours of data for the four categories provided by the API endpoint: Entities, Trip Updates, Vehicles, and Alerts (of which none were observed for these trains during the period). Each category is plotted as a line relative to the time UTC the API was accessed. The Y-axis represents the count for that value at that given time. If the vehicles line reaches 200 at 21:00 UTC, then there were 200 vehicles in active service across the eight trains at that time. 

## Observations

As expected, there is a noticeable uptick in traffic during the traditional work travel hours in morning and evening on weekdays. I was surprised as to how pronounced it still is in the age of hybrid and virtual work, as I expected to see a more even balance across the day. I also observed that service is much higher in the middle of the day than it is before or after the rush hours, supplying trains to those who work differing hours or need to access other resources in the city. One element I observed on Saturday, which had similar service to Sunday and much lower than Friday for the most part, had a noticeable peak of service in the middle of the day. Upon some research, it appears that there was a baseball game at a stadium served by one of the trains included in this data, and service was likely higher to manage the crowds departing the event. Another game was held on Sunday, although a far smaller bump was observed. 

If I were to build this pipeline as an actively functioning system, I would manage access to both AWS and to a potential API with more security. I would also potentially set up a series of files, allowing me or anyone else to go in and find a file containing data for a specific period for any analysis they might want to complete. 