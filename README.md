# Lifeboard

Powered by the **Digital Memoir Engine** (DME), is an interactive reflection space and powerful planning assistant where there is infinite opportunity for discovery and planning. Seamlessly pulling from your digital history—concerts attended, music loved, thoughts shared, places visited, meetings attended —it transforms each day into a personal newspaper. With an AI you can customize —factual, poetic, analytical, or playful—you’ll rediscover meaning in the everyday and take control of your future journey.
  
But you don’t always have to know where to look. Lifeboard invites serendipity through random resurfacing of forgotten moments and AI-guided discovery journeys—because some of life’s richest memories are the ones you didn’t expect to find.  

Beyond reflection, Lifeboard empowers the present and the future.  Your personal assistant will help you keep up with to-dos, pull out insights from business meetings, keep track of important medical appointments, and beyond
  
It’s about seeing anew—with clarity, gratitude, proactive power and wonder.

Lifeboard is open source out of the gate and made to run on your computer and not the cloud. 

## Architecture
- Extremely low cost or free
- Novice facing if at all possible
- Leverage both AI and non-AI solutions (example nltk)
- Extreme modularity and extensability: future-proof design.  Today mem0, tomorrow Langchain.. today SQLlite, tomorrow Postgres
- Extreme abstracion and encapsulation

## Resources and MUST reads
/supporting documents/
/supporting documents/Design/Plan.md
- [UseCortex](https://usecortex.ai/)

## Contributing
- The repository now has a Discussions tab, use it
- Need user's credentials?  The live in secrets.json (secrets.example.json)
- Fork
- Create your feature branch (git checkout -b my-new-feature)
- Run codesmell review, as deep as possible
- Lint (black, isort, flake8)
- Docstrings on all classes and methods
- Ensure abstraction
- Add pytests for the feature in /tests/ .. all must pass
- Run ALL tests prior to PR ..  all must pass