# GLA Plan Formatter

Turns your planning documents into Gibraltar Leadership Academy's official house style: the crest in the header, maroon and gold, one consistent layout for every teacher. It produces Word and PDF.

## What it makes

- Lesson plan (one period)
- Weekly lesson plan (a week, day by day, with Islamic expectations, character education, learning skills, and AFL / AAL / AOL)
- Unit plan (backward design)
- Course outline (the full 19-section GLA outline)
- Short and long term plan
- Exam cover page

## Installing it (once)

1. On claude.ai, open Settings, then Capabilities, then Skills.
2. Upload the file `gla-plan-formatter.skill`.
3. That is all. The skill turns on automatically when you ask for GLA formatting.

To update, upload the newer file the same way. If two copies appear in the list, remove the older one.

## Using it

Start a chat, attach or paste your document (Word, PDF, Google Doc export, Markdown, or plain notes), and say what you want, for example:

- "Format this as a GLA lesson plan."
- "Put my unit plan into the GLA template."
- "Make a GLA course outline from this."
- "I have my course outline. Build me weekly plans for Unit 2."
- "Exam cover page for SBI4U, Semester 1."

The skill asks one short set of questions before it builds: what it found in your document, what is missing, and whether you want it to fill the gaps. Reply "go" to accept everything, or correct any line. Say "just build it" to skip the questions.

## What it will and will not invent

- It keeps your wording, your examples, your names, and your curriculum codes.
- Nothing is marked inside the document itself, so nothing can be submitted with a note left in it. Instead, every build comes with a review list (a short Markdown file named after your course) that says, document by document and section by section, what was drafted, derived, or changed, and what it was based on. The reply names that file first and says the documents are not ready to submit until you have gone through it.
- A missing required part is left blank unless you say it may be filled in, and the review list opens with those blanks under "Gaps: not filled".
- If you ask for a document you do not have yet (weekly plans from an outline, for example), it drafts one from your related documents and the Ontario expectations, and the review list covers every drafted section.

## Tips

- Give the course code, grade, duration, and dates up front and there will be fewer questions.
- The PDF is what the layout is meant to look like. Word may show slightly different spacing; that is normal.
- To find out which version made a file: in Word, File, then Properties, then Summary; the Comments field names the version.

## Questions or layout problems

Contact Br. Zaid. Include the file and a sentence about what looked wrong.
