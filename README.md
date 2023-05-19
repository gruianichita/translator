**Notes**
* App will be exposed at 8001 port, because usually 8000 not free
* Create a local.env file for defining empty variables


**What can be improved in future**
* authorization
* tests for endpoints 
* separate functionality from single main files
* create sql repository
* a HUGE problem is in scrapping, sometimes it doesn't work because there are auto generated tags and not easy to predict what will be a new tags ordering, I tried to find stable solution, tried some libraries, it does not work well, and I have to use Google translate, BUT I read more topics and documentation aboub Google Cloud, there is no solution to get multiple translations, synonyms and definitions, I tried to use just beautiful soup, it does not worked well, because translating is slow and I got just loading page, I implemented mechanisms to await translation and tried to work with this html in memory, but sometimes I didn't get some values from tags and I decided to save file locally and load it in memory, and it works good now