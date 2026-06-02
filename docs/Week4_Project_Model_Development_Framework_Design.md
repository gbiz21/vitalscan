**Model Development and Framework Design:**

**Group 1 - rPPG Signal Extraction Pipeline for VitalScan**

Dare Adediran

Jason Aranha

Germaine Beazer

Abner Bouomo

**Westcliff University**

AIT 500: Concepts of Artificial Intelligence

Professor Desmond Ademiluyi

May, 2026

**\**

**Abstract**

This document provides an overview of the architectural approach and
overall design for Group 1's VitalScan project. Our team will be
responsible for the development of the rPPG Signal Extraction pipeline.
The pipeline will extract heart rate, Heart Rate Variability (HRV), and
a stress index from a thirty second video taken with a smartphone camera
that captures the users' face. The pipeline will include five steps:
face detection and ROI extraction (MediaPipe FaceMesh) extracting the
rPPG pulse signal using the POS Algorithm band-pass filtering to remove
unwanted frequencies and apply FFT based heart rate calculations
calculate HRV and Stress Index from Inter-Beat Intervals output as JSON
via REST API Endpoint.

The above sections provide detail on the structure of all parts of the
pipeline including data flow among each step of the pipeline, between
our pipeline and those developed by the other groups, what parameters
were used to train/initialize each algorithm, how we will handle errors
encountered during execution, and what needs to occur before completion
of the integration process in Week 5. All tasks one through three have
been completed and fully tested at time of writing. Testing for task
four is complete; however, testing for task five (stretch goal) began
last week.

**\**

**Model Development and Framework Design**

**Group 1 - rPPG Signal Extraction Pipeline for VitalScan**

**Introduction**

This is the Week 4 group project report for Group 1 of the VitalScan
project. The VitalScan application seeks to assist individuals with
chronic health issues such as diabetes and hypertension in making better
decision-making regarding their diet at the moment of consumption. In
order to achieve its objectives, Group 1 will provide VitalScan an input
source to capture the user's physiological status at that exact point in
time using a non-clinical apparatus. We plan on accomplishing this
objective via the process of analyzing a 30 second facial video from the
user's perspective. From the video we will extract the user's Heart Rate
(HR), Heart Rate Variability (HRV) and Stress Index based on the slight
color variations in the skin captured by the camera.

Week 3 provided our Week 4 project report with the background and
methodology used to select the methods described above. Therefore, this
Week 4 project report will describe the architectural specifications for
the overall system. The architectural specifications will include;
descriptions of the five stage pipeline; inputs/outputs for each stage
of the pipeline; parameterization of each stage; error handling; and the
integrated development schedule for Weeks 4-5.

Our proposed pipeline is structured in accordance with the methodology
developed by Bawack et al. (2021). Their proposed methodology emphasizes
establishing clear definitions for model architecture, required data,
and evaluation criteria prior to locking in the specific implementation
details. Our pipeline has been defined from stages 1 thru 3, and stage
four is currently being tested. Also, our "stretch goal" (comparing deep
learning methodologies) begins this week.

**Pipeline Architecture Overview**

**Five-Stage Design**

<img
src="/Users/gbeazer/05_Projects/vitalscan/docs/wk4_media/media/image2.png"
style="width:6.5in;height:5.01583in" />

*Figure 2. System architecture - client to Cloudflare tunnel to
containerized backend to JSON contract for Groups 3 & 4.*

The Group 1 Pipeline includes five sequential stages. The stages are
completely independent from each other. They take an input at the
beginning of the stage. Do one job on that input. Then pass their output
to the next stage. That way, we can test them individually and it will
make finding errors easier. All stages of the pipeline are listed below.

**Table 1**

*rPPG Pipeline Stage Overview*

| **Stage** | **Name** | **Input** | **Output** | **Status** |
|----|----|----|----|----|
| 1 | Face Detection and ROI Extraction | Raw video file or camera stream | RGB time-series arrays per ROI zone | Complete |
| 2 | POS Signal Extraction | RGB arrays and fps value | Raw pulse waveform array | Complete |
| 3 | Bandpass Filter and Heart Rate | Raw pulse waveform and fps | Filtered waveform and heart_rate (BPM) | Complete |
| 4 | HRV and Stress Index | Filtered waveform and fps | hrv_sdnn (ms) and stress_index (0-1) | In progress |
| 5 | API Output | All biomarker values | JSON matching shared contract | In progress |

*Note.* Status is current as of the Week 4 submission. Stages 1-3 are
complete and validated on SCAMPS test videos. Stages 4-5 are expected to
be finished before the Week 5 integration milestone.

**Data Flow**

**Through the Pipeline**

The signal-chain diagram in Figure 1 below visualizes the data flow
through stages 1–4. Tensor shapes are annotated at each transition so
the per-stage transform is traceable end-to-end.

<img
src="/Users/gbeazer/05_Projects/vitalscan/docs/wk4_media/media/image1.png"
style="width:6.5in;height:2.48806in" />

*Figure 1. rPPG signal-chain — data flow through stages 1–4.*

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<thead>
<tr>
<th><p>INPUT: 30-second video (MP4 or live stream, 30fps minimum, 720p
minimum)</p>
<p>|</p>
<p>v</p>
<p>[Stage 1: Face Detection - MediaPipe FaceMesh]</p>
<p>- 468 facial landmarks extracted per frame</p>
<p>- ROI bounding boxes defined for forehead, left cheek, right
cheek</p>
<p>- Mean R, G, B computed per ROI per frame</p>
<p>OUTPUT: {forehead: array[N,3], left_cheek: array[N,3],</p>
<p>right_cheek: array[N,3], fps: float}</p>
<p>|</p>
<p>v</p>
<p>[Stage 2: POS Algorithm]</p>
<p>- RGB normalized by temporal mean</p>
<p>- Projected onto plane orthogonal to skin-tone direction</p>
<p>- Waveform averaged across 3 ROI regions</p>
<p>OUTPUT: pulse_waveform: array[N]</p>
<p>|</p>
<p>v</p>
<p>[Stage 3: Bandpass Filter + FFT]</p>
<p>- Butterworth filter (0.7-4.0 Hz, order 4, zero-phase)</p>
<p>- FFT applied to filtered signal</p>
<p>- Peak frequency in HR band converted to BPM</p>
<p>OUTPUT: filtered_waveform: array[N], heart_rate: float</p>
<p>|</p>
<p>v</p>
<p>[Stage 4: HRV and Stress Index]</p>
<p>- Peak detection on filtered waveform</p>
<p>- IBI series = time differences between consecutive peaks (ms)</p>
<p>- SDNN = std(IBI)</p>
<p>- IBI resampled to 4Hz, Welch PSD computed</p>
<p>- LF/HF power ratio normalized to 0.0-1.0</p>
<p>OUTPUT: hrv_sdnn: float (ms), stress_index: float (0.0-1.0)</p>
<p>|</p>
<p>v</p>
<p>[Stage 5: FastAPI /scan endpoint]</p>
<p>- Assembles full JSON per shared contract</p>
<p>- Adds confidence flag and scan metadata</p>
<p>OUTPUT: JSON -&gt; consumed by Group 3 and Group 4</p></th>
</tr>
</thead>
<tbody>
</tbody>
</table>

**\**

**Connection to Other Groups**

Groups 1 JSON output will be delivered to two different destinations.
Group 3 (Biomarker Risk Prediction), takes the biomarkers and puts the
values into a machine learning risk prediction model to create an
individual’s diabetes and hypertension risk score. The NLP/Prompt
Engineering group (Group 4), uses the risk scores from Group 3 and the
food nutrition information from Group 2 to produce the users’
personalized food safety explanation.

For now until we go live with our API, Groups 3 & 4 are using the mock
biomarker data created as part of our shared contract at the beginning
of this project. Our intention is to replace our fake URL with our
actual endpoint URL on the week 5 integration date. To do this, we first
need to get our /scan endpoint to work completely and tested.

**Algorithm Specifications**

**Stage 1: Face Detection and ROI Extraction**

Static Image Mode was set to FALSE when creating an instance of Media
Pipe Face Mesh for Video Input. Min Detection Confidence = .5. Max
Number of Faces = 1. Refine Landmark = TRUE for Sub-Pixel Precision.

Three Region Of Interest (ROI) Zones were created by defining three
different landmark index sets. The Forehead Zone used 36 Indices that
covered the Upper Forehead. Both Cheek Zones used 13 Indices.

For each Frame, the Bounding Box was calculated based on the Landmark
Coordinates. Then, the Bounding Box coordinates were clipped to the
frame boundaries to account for Edge Cases such as Lateral Head Turns.
Finally, the Mean RGB value across all Pixels within the Bounding Box
were calculated and stored in a Time Series for each Region.

**Stage 2: POS Algorithm**

The POS method (Wang et al., 2017), uses the Pos Algorithm on each of
the three Region of Interest (ROI) time series independently. To
eliminate color variations in terms of absolute brightness levels, each
RGB channel is normalized to their individual average time series.
Normalized signals for each ROI are transformed into two additional
channels that include S1 = G-B and S2 = (-2\*R)+G+B. An scaling value of
α = STD(S1)/STD(S2) is calculated as well as a single combined pulse
signal P = S1 +α\*S2. The final step is to take an element-wise average
of the three ROIs to create a single combined pulse signal.

**Stage 3: Bandpass Filter and FFT**

We apply a fourth order Butterworth band pass filter, that has been set
for cut off frequencies of 0.7 Hz and 4.0 Hz (via SciPy's butter and
filtfilt) due to the need to perform zero phase filtering via filtfilt
since any phase shift will result in shifting the beat peaks thus
corrupting the IBI calculations done on the filtered waveforms. The
resultant waveforms are then converted into the frequency domain via the
rfft function of numpy. The peak frequency within the range of 0.7 Hz to
4.0 Hz from this conversion is determined and then multiplied by 60 to
determine BPM.

**Stage 4: HRV and Stress Index**

SciPy’s find_peaks function is used on the filtered signal with an
inter-peak separation of 0.4 sec or less than a 150 bpm max heart rate.
The time stamps for peaks in the wave form are then turned into ms
values. The difference in time between each pair of peak is then
calculated and this is known as the IBI (Inter Beat Interval). The
standard deviation of these intervals is defined as SDNN. To calculate
the Stress Index, the IBI data is interpolated using cubic spline so it
can be uniformly sampled at a frequency of 4 hz. Then Welch PSD
Estimation is performed on this data.

**Stage 5: API Endpoint**

The /scan endpoint will accept a POST of a video file to be uploaded
along with returning a JSON-based representation of an object that will
match the provided common contract. The confidence value in this
representation is determined by the IBI sample count; it will be labeled
as "high" when there are over 25 samples; "medium" when the count is
from 10 through 25; and null (with a note explaining) when the IBI
sample count is less than 10. Since classical rPPG does not have
reliable blood pressure estimations, all blood pressure fields will also
return null.

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<thead>
<tr>
<th><p>POST /scan</p>
<p>Content-Type: multipart/form-data</p>
<p>Body: video_file (MP4, minimum 30 seconds, 720p or higher)</p>
<p>Success response (200):</p>
<p>{</p>
<p>"biomarkers": {</p>
<p>"heart_rate": 74.2,</p>
<p>"hrv_sdnn": 42.1,</p>
<p>"stress_index": 0.58,</p>
<p>"blood_pressure": {</p>
<p>"systolic": null,</p>
<p>"diastolic": null</p>
<p>}</p>
<p>},</p>
<p>"scan_duration_s": 30,</p>
<p>"confidence": "medium",</p>
<p>"ibi_count": 22,</p>
<p>"notes": "BP null by design. Short window may reduce LF/HF
reliability."</p>
<p>}</p>
<p>Error responses:</p>
<p>422 - face_not_detected: no face found in video</p>
<p>400 - video_too_short: video under 25 seconds</p>
<p>500 - processing_error: internal pipeline failure with log
reference</p></th>
</tr>
</thead>
<tbody>
</tbody>
</table>

**\**

**Data Requirements and Validation**

**Input Requirements**

The video for this pipeline requires a 30 second long, 720p, 30fps
video. The face in the video should be looking directly at the camera
and have relatively consistent lighting. This helps to limit flicker or
rapid changes in lighting which could create an artifact within the rPPG
signal that would likely remain after the band pass filtering. Once we
are allowed access to do so, we plan on validating UBFC-rPPG using
real-subject data as well.

**Accuracy Targets**

.

Heart rate accuracy in this project will be determined through
comparison of our results to the ground truth values obtained from
SCAMPS, by measuring both mean absolute error (MAE), as well as root
mean square error (RMSE). For us to receive "full" marks on heart rate
accuracy, we would like to have an MAE below 10 beats per minute (BPM).
To get a "stretch credit," we would want the MAE to be less than 5 BPM.
In a recent five sample preliminary test, we found the average MAE was
about 2.62 BPM, which has been good so far; however, it is too early for
us to feel confident with these results until we evaluate them after
completing all fifty samples in the next week.

**Error Handling**

Three explicit error cases exist. In case of detection failure (i.e., no
face), an appropriate error response is generated using HTTP code 422
that includes a request to the end-user for improvement in lighting and
frontality. If less than ten IBI sample records were obtained, both the
HRV SDNN and Stress Index values will be null; however, a note will be
added to explain why this occurred as an additional aid to allow for
graceful handling by Group 3 and Group 4 models. In addition, if the
recorded video was shorter than 25 seconds, the API will generate an
HTTP code 400 error indicating that a longer record needs to be made.

**Key Parameters**

**Table 2**

*Algorithm Parameter Summary for the rPPG Pipeline*

| **Stage** | **Parameter** | **Value** | **Justification** |
|----|----|----|----|
| 1 - FaceMesh | min_detection_confidence | 0.5 | Balances detection rate and false positives under variable lighting |
| 1 - FaceMesh | refine_landmarks | True | Sub-pixel precision needed for tight ROI bounding boxes |
| 3 - Filter | Filter type | Butterworth order 4 | Flat passband; minimal signal distortion in the HR band |
| 3 - Filter | Bandpass range | 0.7-4.0 Hz | Covers full physiological heart rate range (42-240 BPM) |
| 3 - Filter | Method | filtfilt (zero-phase) | Prevents phase distortion that would shift IBI peak positions |
| 4 - HRV | Peak min distance | 0.4 seconds | Handles up to 150 BPM without double-detecting a single peak |
| 4 - HRV | IBI resampling rate | 4 Hz | Standard for short-window HRV frequency domain analysis |
| 4 - HRV | Welch nperseg | min(N, 64) | Adapts to how many IBI samples are actually available |
| 4 - HRV | LF band | 0.04-0.15 Hz | Standard autonomic frequency band per Task Force (1996) guidelines |
| 4 - HRV | HF band | 0.15-0.40 Hz | Standard autonomic frequency band per Task Force (1996) guidelines |
| 5 - API | Confidence threshold | IBI count over 25 | Enough samples for HRV estimates to be reasonably reliable |

*Note.* Parameter values are consistent with rPPG-Toolbox benchmarking
(Liu et al., 2022) and HRV Task-Force guidelines (European Society of
Cardiology, 1996).

**\**

**Integration Timeline**

**Table 3**

*Week 4 and 5 Milestones for Group 1*

| **Milestone** | **Target** | **Notes** |
|----|----|----|
| Finish Stage 4 HRV and stress index validation | Week 4 | Lomb-Scargle comparison also being evaluated as a potential alternative to Welch for short windows |
| Complete 50-sample MAE/RMSE accuracy run on SCAMPS | Week 4 | Will compare against CHROM baseline from rPPG-Toolbox |
| Finalize /scan endpoint with all fields live | Week 4 | Depends on Stage 4 completion |
| Share API URL with Groups 3 and 4 | End of Week 4 | Groups 3 and 4 can then swap mock data for real calls |
| Start stretch goal - PhysNet accuracy comparison | Week 4 | Will use rPPG-Toolbox pretrained weights |
| Integration day - all groups connect real APIs | Week 5 | End-to-end demo: face scan to food safety explanation |

**Known Limitations**

Firstly, there are three significant limitations that need to be noted
now. The first is the short-window HRV challenge. Using a 30-second scan
provides roughly 20-30 IBI samples; however, the European Society of
Cardiology (1996) recommends no less than five minutes for reliable
LF/HF frequency-domain analysis. Therefore, we consider the stress index
to be a coarse estimate or indicator rather than a clinical measure. In
order to assist Groups 3 and 4 in incorporating this limitation in their
respective models, we include this in each API response via the
confidence flag and note's field.

Secondly, skin tone bias is also an issue. As virtually all of the
previous validation studies of POS algorithms, along with most classical
rPPG methods, have been conducted on relatively fairer skin tones, it
follows that when individuals with darker skin types view themselves,
they absorb more red channel light relative to their skin type and
therefore reduce the signal amplitude. We plan to document the MAE for
available skin tone categories within our SCAMPS study, and this
limitation will be explicitly stated in the user documentation for the
applications.

Lastly, since blood pressure cannot be derived from rPPG using classical
techniques, systolic and diastolic will always be returned as 'null.'
Since this has been well-documented at the onset of the project, Group 3
was aware of this at the project kick-off and incorporated a mechanism
in their risk model to address missing/null values for BP.

**Conclusion**

This document presents the entire architectural and framework design for
Group 1's rPPG Pipeline. The 5-Stage Design provides a modular,
well-defined path from raw smartphone video to a structured JSON
biomarker output. Each stage of the design can be independently
evaluated/tested/updated. The design will follow the AI Research
Framework as presented by Bawack et al. (2021), and it is based upon the
established rPPG literature provided by Wang et al. (2017) and Liu et
al. (2022).

We have completed stages 1 – 3 and are experiencing positive results
with regard to the initial accuracy numbers. We expect to have the
complete pipeline, which includes the REST API, available prior to our
Week 5 Integration Day. Our major objective going forward is completing
the stress index validation in Stage 4, and we have a specific plan for
accomplishing this task this week. As an overall assessment, I believe
the team feels confident in the direction that we are headed with
respect to the second half of the project.

**\
References**

Bawack, R. E., Wamba, S. F., & Carillo, K. D. A. (2021). A framework for
understanding artificial intelligence research: Insights from practice.
Journal of Enterprise Information Management, 34(2), 645-678.
https://doi.org/10.1108/JEIM-07-2020-0284

European Society of Cardiology. (1996). Heart rate variability:
Standards of measurement, physiological interpretation, and clinical
use. Circulation, 93(5), 1043-1065.

Liu, X., Hill, B., Jiang, Z., Panda, S., & McDuff, D. (2022).
rPPG-Toolbox: Deep remote PPG toolbox. arXiv.
https://arxiv.org/abs/2210.00716

McDuff, D., Wander, M., Liu, X., Hill, B. L., Hernandez, J., Lester, J.,
& Baltrusaitis, T. (2022). SCAMPS: Synthetics for camera measurement of
physiological signals. In Advances in Neural Information Processing
Systems (Vol. 35).

Wang, W., den Brinker, A. C., Stuijk, S., & de Haan, G. (2017).
Algorithmic principles of remote-PPG. IEEE Transactions on Biomedical
Engineering, 64(7), 1479-1491. https://doi.org/10.1109/TBME.2016.2609282
