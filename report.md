# RAG evaluation: 4,000-token successful-response subset
## Scope

This report covers **40 successfully generated responses** using a
**4,000-token context budget**: 32 answerable cases and eight challenge cases.
Questions, reference answers, generated answers, selected contexts and individual
metric assessments are retained together.

The evaluation covers document-grounded answering, evidence coverage, response
relevance, false-premise correction and appropriate abstention. 

## Corpus and pipeline

The collection contains ten full official Python 3.12 documentation pages:
pathlib, shutil, venv, os, os.path, tempfile, glob, json, csv and argparse.
The corpus has **256 indexed chunks** and **415,815 extracted characters**.
Only documents were indexed, never questions, references or evaluation labels.

| Python 3.12 document | Subject | Indexed chunks |
|---|---|---:|
| [pathlib](https://docs.python.org/3.12/library/pathlib.html) | Object-oriented paths, file I/O and path resolution | 29 |
| [shutil](https://docs.python.org/3.12/library/shutil.html) | Copying, moving, disk usage and directory cleanup | 18 |
| [venv](https://docs.python.org/3.12/library/venv.html) | Virtual-environment creation and behavior | 14 |
| [os](https://docs.python.org/3.12/library/os.html) | Directory traversal, permissions and filesystem operations | 98 |
| [os.path](https://docs.python.org/3.12/library/os.path.html) | Path expansion, prefixes and symbolic-link checks | 11 |
| [tempfile](https://docs.python.org/3.12/library/tempfile.html) | Temporary files, directories and resource lifetimes | 10 |
| [glob](https://docs.python.org/3.12/library/glob.html) | Wildcard matching, iteration and escaping | 3 |
| [json](https://docs.python.org/3.12/library/json.html) | Serialization, parsing and value representation | 15 |
| [csv](https://docs.python.org/3.12/library/csv.html) | Readers, writers, headers and field conversion | 12 |
| [argparse](https://docs.python.org/3.12/library/argparse.html) | Argument cardinality, conversion and boolean flags | 46 |
| **Total corpus** | **10 complete documentation pages** | **256** |

The pipeline uses:

- Local embeddings, 384 dimensions.
- OpenSearch dense and sparse retrieval, 20 candidates each.
- Reciprocal-rank fusion, followed by cross-encoder reranking to the top eight.
- Prefix context selection within a 4,000-token estimated budget.
- Generation with input and output guardrails.

The budget uses the application's character-based token estimate. It is not the
answer-output limit or the total supported context capacity.


## Retained case distribution

| Category | Successfully generated responses | Share of retained set | Expected behavior |
|---|---:|---:|---|
| Direct, single-document | 23 | 57.5% | Answer a documented API or behavior question |
| Comparison / multi-section or multi-document | 9 | 22.5% | Distinguish related APIs or combine evidence |
| False-premise correction | 5 | 12.5% | Correct the question's incorrect assumption |
| Missing-answer / out-of-corpus | 3 | 7.5% | State that the documents do not establish the fact |
| **Total** | **40** | **100%** | |

The first two categories form the 32 answerable cases; the other two form the
eight challenge cases. Original case IDs are preserved for traceability and are
not renumbered to imply a newly sampled dataset.

The nine comparisons comprise five cross-document and four within-document
cases. Direct questions are distributed across all ten documents in this subset. The exact question wording is listed in the appendix, reference answers and selected contexts are in the linked evaluation data.

## RAGAS results

Evaluation used **RAGAS 0.4.3**. This report presents four selected metrics for
the 32 answerable responses, plus a separate behavior rubric for the eight
challenge responses. All displayed metrics have full judge coverage for their stated response counts.

| Metric | Mean | Scored responses | Scale |
|---|---:|---:|---|
| Faithfulness | **0.894912** | 32 | 0-1 |
| Answer accuracy | **0.968750** | 32 | 0-1 |
| Context recall | **0.963542** | 32 | 0-1 |
| Answer relevancy | **0.881120** | 32 | 0-1 |
| Challenge behavior rubric | **5.000000** | 8 | 1-5 |

Accuracy uses two validated judge ratings per response. Answer relevancy uses
three validated generated reverse questions per response with locally computed
embeddings. Validated assessments from the same retest's smoke test were
reused without scoring those inputs again.

Context recall evaluates the contexts selected **after reranking and budget
selection**, not raw OpenSearch retrieval. There is no combined
overall score; the metrics measure different properties.

| Reported metric | What it measures |
|---|---|
| Faithfulness | Whether answer claims are supported by the selected contexts |
| Answer accuracy | Agreement with the question-aware reference answer |
| Context recall | Whether selected contexts contain the information needed for the reference |
| Answer relevancy | Alignment with the question, using generated reverse questions |
| Challenge behavior rubric | Whether the response corrects a false premise or appropriately abstains |

## Evidence selection and resource use

For the 32 retained answerable cases, **55/60 predeclared required evidence groups
(91.67%)** were present in selected context, and **27/32 cases** contained every
required group. These quote-locator measurements are distinct from RAGAS recall.
All 40 responses passed structural source-mapping, chunk-count and citation-label
checks; these checks do not prove that citations substantiate every claim.



## Retained evidence

- [Normalized questions, references, answers and contexts](evaluation_data/runs/python-docs-40-4000/samples.jsonl)

The linked data contains the 40 retained successful responses. Questions, answers, references and contexts were preserved unchanged. 

## Appendix: exact retained questions

These are the actual question wordings used for the retained 4,000-token
responses, not newly written examples. False-premise questions intentionally
contain incorrect assertions. The organization-specific questions are synthetic
missing-answer probes; they do not imply that the corpus contains internal facts.

### Direct questions: 23

| Case ID | Document | Question |
|---|---|---|
| py50-01 | pathlib | For Python 3.12 Path.iterdir, is directory-entry ordering guaranteed, and what happens if the directory contents change after the iterator is created? |
| py50-02 | pathlib | When Python 3.12 Path.write_text is called on an existing text file, does it append or overwrite, and does it close the file? |
| py50-03 | pathlib | In Python 3.12, which Path.unlink argument suppresses a missing-file error, and is unlink the operation for removing a directory? |
| py50-04 | shutil | In Python 3.12 shutil.copytree, how can copying continue when destination directories already exist, and what happens to corresponding files in the destination? |
| py50-05 | shutil | How does Python 3.12 shutil.move implement a move when source and destination are on different filesystems? |
| py50-06 | shutil | Which fields and units does Python 3.12 shutil.disk_usage return? |
| py50-10 | os | In Python 3.12 os.walk, what does followlinks default to, and what risk arises when it is enabled? |
| py50-11 | os | Does Python 3.12 os.makedirs apply the supplied mode to all intermediate directories, and does it change permissions on existing parents? |
| py50-12 | os | In Python 3.12 os.scandir, can I rely on entry order or on changes made to the directory after the iterator is created being reflected? |
| py50-14 | os.path | What does Python 3.12 os.path.expanduser expand at the beginning of a path? |
| py50-15 | os.path | In Python 3.12, does os.path.commonprefix necessarily return a valid filesystem path? |
| py50-16 | tempfile | What cleanup behavior does Python 3.12 tempfile.TemporaryDirectory provide when used in a with statement? |
| py50-17 | tempfile | What values does Python 3.12 tempfile.mkstemp return, and who is responsible for deleting the created file? |
| py50-18 | tempfile | Does Python 3.12 tempfile.mkdtemp automatically delete its directory, and is its returned path absolute even for a relative dir argument? |
| py50-19 | glob | Does Python 3.12 glob.glob guarantee results are sorted, and can it include broken symbolic links? |
| py50-21 | glob | Which pattern characters does Python 3.12 glob.escape escape, and does it escape special characters in drive or UNC sharepoint portions? |
| py50-23 | json | In Python 3.12 json.dump, how do I reject NaN and Infinity instead of writing JavaScript-style values? |
| py50-24 | json | Which exception does Python 3.12 json.loads raise when the input is not a valid JSON document? |
| py50-25 | csv | When reading CSV from a file object in Python 3.12, what newline setting is recommended, and are ordinary reader fields automatically converted to numbers? |
| py50-26 | csv | What does Python 3.12 csv.writer write for None, and is that transformation reversible? |
| py50-27 | csv | How does Python 3.12 csv.DictReader obtain field names when fieldnames is omitted, and is that first row returned as data? |
| py50-28 | argparse | What does nargs='?' mean for an optional argument in Python 3.12 argparse when the option is absent versus present with no value? |
| py50-30 | argparse | With type=int and choices configured in Python 3.12 argparse, are choice checks applied before or after conversion? |

### Comparison questions: nine

| Case ID | Documents | Question |
|---|---|---|
| py50-31 | pathlib, json | How do Python 3.12 Path.read_text and json.loads work together to read a JSON file, and how does that differ from json.load's input? |
| py50-32 | tempfile | In Python 3.12, how does the lifetime of a file created by tempfile.mkstemp differ from one managed by tempfile.TemporaryFile in a with statement? |
| py50-33 | glob | Compare the result forms of Python 3.12 glob.glob and glob.iglob when a large number of paths matches a pattern. |
| py50-34 | os.path | For a broken symbolic link in Python 3.12, how do os.path.exists and os.path.lexists differ? |
| py50-35 | shutil, os | In Python 3.12, how do shutil.move and os.replace differ when moving a path across filesystem boundaries? |
| py50-36 | csv, json | Why can the documented Python 3.12 csv.writer behavior lose a distinction that json.dumps preserves when serializing None versus an empty string? |
| py50-37 | argparse | In Python 3.12 argparse, how do nargs='*' and nargs='+' differ when no positional arguments are provided? |
| py50-39 | tempfile, shutil | How do Python 3.12 tempfile.TemporaryDirectory and shutil.rmtree differ in when a directory tree is removed? |
| py50-40 | os.path, pathlib | In Python 3.12, can I assume os.path.abspath resolves symbolic links in the same way as Path.resolve? |

### False-premise correction questions: five

| Case ID | Document | Question |
|---|---|---|
| py50-41 | os.path | Because Python 3.12 os.path.commonprefix compares whole path components, can I use it as a guaranteed valid parent directory? |
| py50-42 | json | Since Python 3.12 json.dumps returns UTF-8 bytes, can I pass its result directly to an API that accepts bytes only? |
| py50-43 | csv | Because every Python 3.12 csv.reader field is converted to a number automatically, can I skip explicit conversion for ordinary CSV input? |
| py50-44 | glob | Python 3.12 glob.glob always sorts its matches, so can I rely on its first match being alphabetically smallest? |
| py50-45 | argparse | Since Python 3.12 argparse requires type=bool for a reliable on/off flag, should I use type=bool to make the string False become a false value? |

### Missing-answer questions: three

| Case ID | Question |
|---|---|
| py50-46 | What CSV delimiter did our customer-import team approve for its November 2026 production feed? |
| py50-48 | What temporary-file retention period has our organization approved for its internal batch jobs? |
| py50-49 | What exact command-line switches does our unpublished in-house backup utility accept? |

## Third-party documentation notices

The linked evaluation data contains excerpts from the official
[Python 3.12 documentation](https://docs.python.org/3.12/), authored by the
Python Software Foundation and Python documentation contributors.

Copyright © 2001-2023 Python Software Foundation; All Rights Reserved.

The documentation is distributed under the
[Python Software Foundation License Version 2](https://docs.python.org/3.12/license.html).
The following notice applies to the reproduced documentation, not to the
project's independently authored code or evaluation results.

Changes for this evaluation: documentation bodies were extracted from HTML,
navigation and permalink controls were removed, text and whitespace were
normalized, and excerpts were selected as evaluation contexts. Questions,
references and generated responses were added separately. No changes were made
to Python itself. These notices accompany the excerpt-containing evaluation data
and should be retained when redistributing it.

<details>
<summary>Python Software Foundation License Version 2 — full text</summary>

PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2

1. This LICENSE AGREEMENT is between the Python Software Foundation ("PSF"), and
   the Individual or Organization ("Licensee") accessing and otherwise using this
   software ("Python") in source or binary form and its associated documentation.

2. Subject to the terms and conditions of this License Agreement, PSF hereby
   grants Licensee a nonexclusive, royalty-free, world-wide license to reproduce,
   analyze, test, perform and/or display publicly, prepare derivative works,
   distribute, and otherwise use Python alone or in any derivative
   version, provided, however, that PSF's License Agreement and PSF's notice of
   copyright, i.e., "Copyright © 2001-2023 Python Software Foundation; All Rights
   Reserved" are retained in Python alone or in any derivative version
   prepared by Licensee.

3. In the event Licensee prepares a derivative work that is based on or
   incorporates Python or any part thereof, and wants to make the
   derivative work available to others as provided herein, then Licensee hereby
   agrees to include in any such work a brief summary of the changes made to Python.

4. PSF is making Python available to Licensee on an "AS IS" basis.
   PSF MAKES NO REPRESENTATIONS OR WARRANTIES, EXPRESS OR IMPLIED.  BY WAY OF
   EXAMPLE, BUT NOT LIMITATION, PSF MAKES NO AND DISCLAIMS ANY REPRESENTATION OR
   WARRANTY OF MERCHANTABILITY OR FITNESS FOR ANY PARTICULAR PURPOSE OR THAT THE
   USE OF PYTHON WILL NOT INFRINGE ANY THIRD PARTY RIGHTS.

5. PSF SHALL NOT BE LIABLE TO LICENSEE OR ANY OTHER USERS OF PYTHON
   FOR ANY INCIDENTAL, SPECIAL, OR CONSEQUENTIAL DAMAGES OR LOSS AS A RESULT OF
   MODIFYING, DISTRIBUTING, OR OTHERWISE USING PYTHON, OR ANY DERIVATIVE
   THEREOF, EVEN IF ADVISED OF THE POSSIBILITY THEREOF.

6. This License Agreement will automatically terminate upon a material breach of
   its terms and conditions.

7. Nothing in this License Agreement shall be deemed to create any relationship
   of agency, partnership, or joint venture between PSF and Licensee.  This License
   Agreement does not grant permission to use PSF trademarks or trade name in a
   trademark sense to endorse or promote products or services of Licensee, or any
   third party.

8. By copying, installing or otherwise using Python, Licensee agrees
   to be bound by the terms and conditions of this License Agreement.

</details>
