Name: Content Dreamer.ai
Description: It is an app that will dream up content idea based on your product name and description. User will enter product name and description and app will fetch tweets, trends and then generate ideas for content(Articles and tweets)
Frontend(client folder): React, nextjs
Backend(server folder): Python, flask, sqlalchemy, python-rq(for bg tasks)
Tasks:
* create landing page that convert and loads fast and SEO friendly. Make it professional, premium and slick design
* On landing page it should have a "Try It" which will ask user to enter product name and description. which will record these on a table and kick of background job for content report generation. If the user is not logged in, frontend will generate a unique ID and store it in Cookie and pass it during initiate report generation call. Later when user is logged in we will merge these reports created by IDs in their cookie. Each Guest user can generate one report generation request and once report is generated we will display it partially on the frontend and prompt user to login to unlock full content Suggestions, Once logged in user can view rest of the content suggestions and Create More content suggestion, Add new Product etc. After Login they also need to subscribe. There will be 3 subscription tier(basic, pro, advance) with pricing $5, $15, $50, first tier only on product and 1 content suggestion generation per day, 2nd tier upto 5 products, 5 content generation, and 3rd unlimited. make it so these features are easily configurable from single Place

* Now lets talk about how the reports UI will look like, it is basically will be scrolls of content suggestions(article headline and tweets text) for articles there will be a button to generate full article content(which will require subscribing to a subscription plan, 1 generation per day for basic, 5 generation per day for pro, and unlimited for advanced). Users can generate a new list of content suggestions if their subscription tier supports(their old list should still be accessible)

* Now lets talk about how content suggestion generation algorithm will work:
**(Make sure database model for report generation have necessary fields to hold anything that is being fetched at every step and appropriate status being communicated to frontend)**
1. We will use LLM chat(Open ai gpt5) by passing product name and description in the context and ask it to
- Find Keywords prospective clients write about on twitter - group 1
- Find keywords People search on google - group 2
2. We use serpapi google autocomplete search api
    - Expand the keywords list using Google autocomplete suggestions
3. We maintain a table on database and store these
4. We use twttr API from rapid api to 
    - Fetch Trending Twitter Trending Topics and then use LLM(gpt5) to find topics could be most related to Product
    - Fetch 5 top and latest tweets for each Topics selected from above steps
    - Fetch 5 top and latest tweets for each keywords in group1(keywords prospective clients write about on twitter)
    - Fetch 5 top and latest tweets for each keywords in group2(expanded list of keywords people search on google related to our product)
5. User medium api from rapid api
    - fetch root tags from medium( if not already fetched and cached since this should be same for all products)
    - use gpt5 to find tags related to our product
    - Fetch trending articles for each tags from above step

6. Using GPT5 Generate Article Headline Suggestion for each related twitter trending topic(fetched and filtered for related to product) (we will provide latest and top tweets in the context)
7. Using GPT5 Generate potential tweets for each twitter trending topic(fetched and filtered for related to product)
8. for each keyword in group2 generate interesting Article Headline Suggestions (passing fetched tweets once and then again without)
9. for each tags from medium generate interesting Article headline by passing trending articles.
10. for every tweets fetched during this session, use GPT5 to generate interesting witty response(and then rank the responses based on quality and include only top 5 in the report)

* Now talk about article generation. We will initially only display Suggestion Article headline and once user clicks on generate button we will use GPT5 to generate full content and then show it in in a nice TextEditor(Make sure it is the best and state of art in terms of UI and UX)

Make sure view is professional and premium 
Using existing endpoint for login and singup and create New endpoints for the features.






