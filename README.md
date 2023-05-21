**Notes**
* App will be exposed at 8001 port, because usually 8000 not free
* Create a local.env file for defining empty variables


**What can be improved in future**
* authorization
* tests for endpoints 
* separate functionality from single main files
* create sql repository
* create more branches in repo
* add filter by language
* a HUGE problem is in scrapping, sometimes it doesn't work because there are auto generated tags and not easy to predict what will be a new tags ordering, I tried to find stable solution, tried some libraries, it does not work well, and I have to use Google translate, BUT I read more topics and documentation aboub Google Cloud, there is no solution to get multiple translations, synonyms and definitions, I tried to use just beautiful soup, it does not worked well, because translating is slow and I got just loading page, I implemented mechanisms to await translation and tried to work with this html in memory, but sometimes I didn't get some values from tags and I decided to save file locally and load it in memory, and it works good now

**Conclusion** <br>
This is my vision of solving this problem, I configured all you need to work with and I did a part of solution. <br>I left a TODO note where to add the same functionality as with translations, but with definitions, synonyms and examples, just to investigate xpath of blocks and to find them. <br>An investigation will take a lot of my time and effort, but I want to save it for future interviews))

**An important note** <br>
I really want to know your solution, 
I will be thankful if you will write me your solution to my email gruianichita@gmail.com