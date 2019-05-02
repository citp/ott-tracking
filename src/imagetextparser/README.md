# Google Cloud Vision Wrapper

### Usage

python3 cloudvisiontextparser.py <IMAGE_DIRECTORY> <JSON_OUTPUT_DIRECTORY> <NUMBER_OF_THREADS>

## Data Structure

- JSON Structure

Each JSON file contains a list of all of the screenshots for a channel sorted by timestamp.  

Each list element contains the dictionary seen below.

```
timestamp  -  1553810797  (int)
customLabels              (list)
	['LOGIN', 'ACTIVATION', 'DUPLICATE']
labels                    (list)
	['Text', 'Technology', 'Electronic device', 'Multimedia', 'Font', 'Numeric keypad', 'Computer keyboard', 'Space bar', 'Screenshot', 'Input device']
labelScores               (dict)
	Text
		0.9189756512641907
	Technology
		0.8678937554359436
	Electronic device
		0.8632897138595581
	Multimedia
		0.8190076947212219
	Font
		0.7825835347175598
	Numeric keypad
		0.7704290151596069
	Computer keyboard
		0.7640560865402222
	Space bar
		0.7192355394363403
	Screenshot
		0.7167678475379944
	Input device
		0.7101051211357117
textBody                  (string)
	Enter your Pure Flix email address
	Visit pureflix.com/forgotpassword	
textBodyBoundsX           (list)
	[215, 1070, 1070, 215]
textBodyBoundsY           (list)
	[99, 99, 685, 685]
words                     (list)
	['Enter', 'your', 'Pure', 'Flix', 'email', 'address', 'Visit', 'pureflix.com/forgotpassword']
wordBoundsX               (dict)
	Enter
		[404, 478, 478, 404]
	your
		[486, 549, 549, 486]
	Pure
		[557, 618, 618, 557]
	Flix
		[629, 675, 675, 629]
	email
		[684, 757, 757, 684]
	address
		[765, 873, 873, 765]
	Visit
		[460, 498, 498, 460]
	pureflix.com/forgotpassword
		[510, 812, 812, 510]
wordBoundsY                (dict)
	Enter
		[100, 100, 122, 122]
	your
		[106, 106, 125, 125]
	Pure
		[100, 100, 121, 121]
	Flix
		[99, 99, 121, 121]
	email
		[100, 100, 121, 121]
	address
		[101, 101, 121, 121]
	Visit
		[666, 666, 685, 685]
	pureflix.com/forgotpassword
		[666, 666, 685, 685]
SSIM                       (int)
	0.9999999847703207
```

- Explanation of Fields

```
timestamp  
    Timestamps of the image
customLabels
	List of custom labels applied based on the labels from Cloud Vision
labels
	List containing each of the label from Cloud Vision
labelScores
	Dictionary containing the Cloud Vision scores for each label
textBody
	The entire text body as one formatted string
textBodyBoundsX
	X axis bounding box coordinates for the entire text body
textBodyBoundsY
	Y axis bounding box coordinates for the entire text body
words
	List of each individual word detected in the image
wordBoundsX
    X axis bounding box coordinates for each word
wordBoundsY
    Y axis bounding box coordinates for each word
SSIM
    Similarity of screenshot to the last screenshot.  Calculated using the Structural Similarity Index.
```
