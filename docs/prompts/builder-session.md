# Builder session prompts (Claude Code)

Every prompt the Lead (Matt) typed into the Claude Code **Builder** session for this task, verbatim and
in order (times UTC, 2026-10-14). Typos and dictation are left as typed. Pasted Codex output is
moved to its own file and linked. One paste of a review of a *different* repository (pasted by
mistake) is omitted. The Builder's replies are not included; the decisions they led to are in
[`PLAN.md`](../../PLAN.md) and [`NOTES.md`](../../NOTES.md).

### 1. 13:31

> hey

### 2. 13:47

> @"/Users/Matt/Downloads/SOUS Assignment/Senior_Engineer_Assessment_SOUS.pdf"
> We don't need to import the CSV. We will only use the endpoint - and single transactions - no batching.
>
> The repo is: 
>
> https://github.com/Exponenture/sous-transaction

### 3. 13:56

> Um, the CSV has some errors in terms of, uh, I think it is the sign and type disagreement. Um, some of the things that you have seen, timestamps of no time zone, um, etc. Um, we are going to assume that information coming in is going to be dirty, so we need to handle the exceptions in code.
>
> We will need to ensure that all dodgy data is quarantined and labelled for human review

### 4. 13:59

> We need to flag any transactions that don't work logically.  We can assume the timezone is from one local for this

### 5. 14:02

> yes please

### 6. 14:04

> approved, commit and push the spec

### 7. 14:09

_[Pasted the Tester's proposed test plan: [codex-test-plan.md](codex-test-plan.md)]_

Happy with the tests?

### 8. 14:11

> yes, add the amendments and push

### 9. 14:14

> I have an anthopic key, can you template it in .env

### 10. 14:16

> Keys is in .env
>
> Tests are written. goog to go

### 11. 14:26

> Can you sort out the docker port please

### 12. 14:29

> I need a little more info on the prompt to the LLM.

### 13. 14:37

> please ensure the plan is updated

### 14. 14:39

> Should wrong JSON types get the field’s invalid_* code? - pleas  unpack this I don't undersatnd fully

### 15. 14:40

> go with option 1, record it in the plan

### 16. 14:41

> Is the prompt’s location under backend/ OK? Yes

### 17. 14:44

> I want view the code for the post endpoint

### 18. 15:09

> please continue

### 19. 15:16

> commit the csv please

### 20. 15:16

> open the PR

### 21. 15:24

_[Pasted Codex adversarial review: [reviews/round-1.md](reviews/round-1.md)]_

Adverserial Code review from  CODEX

### 22. 15:26

> agree with triage, go with your NUL recommendation

### 23. 15:31

> does the endpoint work?

### 24. 15:32

> tests are written, fix R3-R6

### 25. 15:35

> yes, push it and open PR #2

### 26. 15:42

_[Pasted a Codex review of a different repository by mistake; omitted.]_

### 27. 15:43

> aha. I used the wrong folder 'melting' trying again now

### 28. 15:46

_[Pasted Codex adversarial review: [reviews/round-2.md](reviews/round-2.md)]_

### 29. 15:50

> yes, go with AM8

### 30. 15:51

> are you happy with the tests?

### 31. 15:53

> check again, tests should be there now

### 32. 15:57

> test committed locally

### 33. 15:58

> lets go

### 34. 16:03

> your own reasoning for the stack choice in the README;
>
> Stack was selected to match the SOUS stack as per Offerzn's profile - This is not the Lead's native stack and, as such, some concessions on code walk-through could be made. 
>
> Yes, Please export all prompts
>
> I'll make the repo public. 
>
> Also, Can you please check all the concluded parts in the plan doc.
