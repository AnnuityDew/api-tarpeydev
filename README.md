# tarpey.dev API
API for my apps hosted at [tarpey.dev](tarpey.dev/). **(Feedback is welcome - I'm self-taught and looking to learn more!)**

## URLs
* Live: [api.tarpey.dev](https://api.tarpey.dev/)
* Preview: [dev-api.tarpey.dev](https://dev-api.tarpey.dev) (unless I broke something)

## Key Packages
* Built with [FastAPI](https://fastapi.tiangolo.com)
* [ODMantic](https://github.com/art049/odmantic) (async ODM for MongoDB, based on Motor. Enabled painless integration with FastAPI and pydantic!)
* [orjson](https://github.com/ijl/orjson) (speedier and gave me less trouble when working with JSON)
* [Pandas](https://pandas.pydata.org) and [NumPy](https://numpy.org)
* [Okta JWT](https://pypi.org/project/okta-jwt/) (for securing some endpoints)

## Technology Stack
* Hosted on Google Cloud Run (fully managed)
* MongoDB Atlas Free Tier
* Python 3.8+
* For the frontend stack, [visit the frontend repo](https://github.com/AnnuityDew/next-tarpeydev)

## References
* [FastAPI — How to add basic and cookie authentication](https://medium.com/data-rebels/fastapi-how-to-add-basic-and-cookie-authentication-a45c85ef47d3)
* [https with url_for](https://github.com/encode/starlette/issues/538)
* Good JWT articles:
  * [Build and Secure an API in Python with FastAPI](https://developer.okta.com/blog/2020/12/17/build-and-secure-an-api-in-python-with-fastapi)
  * [The Ultimate Guide to handling JWTs on frontend clients (GraphQL)](https://hasura.io/blog/best-practices-of-using-jwt-with-graphql/)
  * [Where to Store your JWTs](https://stormpath.com/blog/where-to-store-your-jwts-cookies-vs-html5-web-storage)
* [Accessing request.state directly in starlette](https://stackoverflow.com/questions/63273028/fastapi-get-user-id-from-api-key)
* [Docker file system](https://stackoverflow.com/questions/20813486/exploring-docker-containers-file-system)
* [Best practices for packaging](https://blog.ionelmc.ro/2014/05/25/python-packaging/)
* Great issues to reference when using MongoDB with FastAPI:
  * [FastApi & MongoDB - the full guide](https://github.com/tiangolo/fastapi/issues/1515)
  * [Recommended way to use mongodb with FastAPI](https://github.com/tiangolo/fastapi/issues/452)
* Multiprocessing (currently not in use, but a good learning experience):
  * [How to do multiprocessing in FastAPI](https://stackoverflow.com/questions/63169865/how-to-do-multiprocessing-in-fastapi)
  * [Comment by Mixser](https://github.com/tiangolo/fastapi/issues/1487#issuecomment-657290725)
  * [Things I Wish They Told Me About Multiprocessing in Python](https://www.cloudcity.io/blog/2019/02/27/things-i-wish-they-told-me-about-multiprocessing-in-python/)
  * [Proper way to use multiprocessor.Pool in a nested loop](https://stackoverflow.com/questions/20387510/proper-way-to-use-multiprocessor-pool-in-a-nested-loop)
  * [When should we call multiprocessing.Pool.join?](https://stackoverflow.com/questions/38271547/when-should-we-call-multiprocessing-pool-join)
* Pandas techniques:
[Select rows in pandas MultiIndex DataFrame](https://stackoverflow.com/questions/53927460/select-rows-in-pandas-multiindex-dataframe)
(https://stackoverflow.com/questions/26046208/normalize-dataframe-by-group)
[Normalize DataFrame by group](https://rtyley.github.io/bfg-repo-cleaner/)