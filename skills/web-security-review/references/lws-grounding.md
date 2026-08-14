<!--
  GENERATED FILE — do not edit by hand.
  Source: lws-knowledge — dist/profiles/module-code/lws-grounding.md
    (https://github.com/salesforce-experience-platform-emu/lws-knowledge, ref main)
  The "module-code" profile: the canonical guide with the block-global-object-
  property-assignment reviewer's LWC-import gate broadened to module code.
  Vendored so the plugin is self-contained (no build, no MCP server, no repo
  dependency at scan time).
  Regenerate: node scripts/extract-guide.mjs
-->

Lightning Web Security (LWS) Analysis Assistant
----------------------------------------------------------------
The following topics, each with their own grounding, are separated by a line of dashes and a new H1 header. Treat each topic as a separate grounding.
These topics can be used to analyze any Lightning Web Components code, as well as any JavaScript or TypeScript code. The code being analyzed DOES NOT HAVE TO BE LWC CODE.
----------------------------------------------------------------
The following definitions are CRITICAL, DO NOT IGNORE THEM:
- "Built-in object" refers to any object that is part of the core JavaScript language.
- "Host object" refers to any object that is not a built-in object or a custom object created by the component. Host objects are defined by the "Web API" or "DOM API"
- "Web API" or "DOM API" refers to the set of objects and methods defined by the HTML and DOM standards and includes all of the following: AbortController, AbortSignal, AbsoluteOrientationSensor, AbstractRange, Accelerometer, AICreateMonitor, alert, AnalyserNode, Animation, AnimationEffect, AnimationEvent, AnimationPlaybackEvent, AnimationTimeline, AsyncDisposableStack, atob, Attr, Audio, AudioBuffer, AudioBufferSourceNode, AudioContext, AudioData, AudioDecoder, AudioDestinationNode, AudioEncoder, AudioListener, AudioNode, AudioParam, AudioParamMap, AudioProcessingEvent, AudioScheduledSourceNode, AudioSinkInfo, AudioWorklet, AudioWorkletNode, AuthenticatorAssertionResponse, AuthenticatorAttestationResponse, AuthenticatorResponse, BackgroundFetchManager, BackgroundFetchRecord, BackgroundFetchRegistration, BarcodeDetector, BarProp, BaseAudioContext, BatteryManager, BeforeInstallPromptEvent, BeforeUnloadEvent, BiquadFilterNode, Blob, BlobEvent, Bluetooth, BluetoothCharacteristicProperties, BluetoothDevice, BluetoothRemoteGATTCharacteristic, BluetoothRemoteGATTDescriptor, BluetoothRemoteGATTServer, BluetoothRemoteGATTService, BluetoothUUID, blur, BroadcastChannel, BrowserCaptureMediaStreamTrack, btoa, ByteLengthQueuingStrategy, Cache, caches, CacheStorage, cancelAnimationFrame, cancelIdleCallback, CanvasCaptureMediaStreamTrack, CanvasGradient, CanvasPattern, CanvasRenderingContext2D, CaptureController, captureEvents, CaretPosition, CDATASection, ChannelMergerNode, ChannelSplitterNode, ChapterInformation, CharacterBoundsUpdateEvent, CharacterData, chrome, clearInterval, clearTimeout, clientInformation, Clipboard, ClipboardEvent, ClipboardItem, close, closed, CloseEvent, CloseWatcher, CommandEvent, Comment, CompositionEvent, CompressionStream, confirm, console, ConstantSourceNode, ContentVisibilityAutoStateChangeEvent, ConvolverNode, CookieChangeEvent, cookieStore, CookieStore, CookieStoreManager, CountQueuingStrategy, createImageBitmap, Credential, credentialless, CredentialsContainer, CropTarget, crossOriginIsolated, crypto, Crypto, CryptoKey, CSPViolationReportBody, CSS, CSSAnimation, CSSConditionRule, CSSContainerRule, CSSCounterStyleRule, CSSFontFaceRule, CSSFontFeatureValuesRule, CSSFontPaletteValuesRule, CSSGroupingRule, CSSImageValue, CSSImportRule, CSSKeyframeRule, CSSKeyframesRule, CSSKeywordValue, CSSLayerBlockRule, CSSLayerStatementRule, CSSMarginRule, CSSMathClamp, CSSMathInvert, CSSMathMax, CSSMathMin, CSSMathNegate, CSSMathProduct, CSSMathSum, CSSMathValue, CSSMatrixComponent, CSSMediaRule, CSSNamespaceRule, CSSNestedDeclarations, CSSNumericArray, CSSNumericValue, CSSPageRule, CSSPerspective, CSSPositionTryDescriptors, CSSPositionTryRule, CSSPositionValue, CSSPropertyRule, CSSRotate, CSSRule, CSSRuleList, CSSScale, CSSScopeRule, CSSSkew, CSSSkewX, CSSSkewY, CSSStartingStyleRule, CSSStyleDeclaration, CSSStyleRule, CSSStyleSheet, CSSStyleValue, CSSSupportsRule, CSSTransformComponent, CSSTransformValue, CSSTransition, CSSTranslate, CSSUnitValue, CSSUnparsedValue, CSSVariableReferenceValue, CSSViewTransitionRule, CustomElementRegistry, customElements, CustomEvent, CustomStateSet, DataTransfer, DataTransferItem, DataTransferItemList, DecompressionStream, DelayNode, DelegatedInkTrailPresenter, DeviceMotionEvent, DeviceMotionEventAcceleration, DeviceMotionEventRotationRate, DeviceOrientationEvent, devicePixelRatio, DevicePosture, DisposableStack, document, Document, DocumentFragment, documentPictureInPicture, DocumentPictureInPicture, DocumentPictureInPictureEvent, DocumentTimeline, DocumentType, DOMError, DOMException, DOMImplementation, DOMMatrix, DOMMatrixReadOnly, DOMParser, DOMPoint, DOMPointReadOnly, DOMQuad, DOMRect, DOMRectList, DOMRectReadOnly, DOMStringList, DOMStringMap, DOMTokenList, DragEvent, DynamicsCompressorNode, EditContext, Element, ElementInternals, EncodedAudioChunk, EncodedVideoChunk, ErrorEvent, event, Event, EventCounts, EventSource, EventTarget, external, External, EyeDropper, FeaturePolicy, FederatedCredential, fence, Fence, FencedFrameConfig, fetch, fetchLater, FetchLaterResult, File, FileList, FileReader, FileSystemDirectoryHandle, FileSystemFileHandle, FileSystemHandle, FileSystemObserver, FileSystemWritableFileStream, find, Float16Array, focus, FocusEvent, FontData, FontFace, FontFaceSetLoadEvent, FormData, FormDataEvent, FragmentDirective, frameElement, frames, GainNode, Gamepad, GamepadButton, GamepadEvent, GamepadHapticActuator, Geolocation, GeolocationCoordinates, GeolocationPosition, GeolocationPositionError, getComputedStyle, getScreenDetails, getSelection, GPU, GPUAdapter, GPUAdapterInfo, GPUBindGroup, GPUBindGroupLayout, GPUBuffer, GPUBufferUsage, GPUCanvasContext, GPUColorWrite, GPUCommandBuffer, GPUCommandEncoder, GPUCompilationInfo, GPUCompilationMessage, GPUComputePassEncoder, GPUComputePipeline, GPUDevice, GPUDeviceLostInfo, GPUError, GPUExternalTexture, GPUInternalError, GPUMapMode, GPUOutOfMemoryError, GPUPipelineError, GPUPipelineLayout, GPUQuerySet, GPUQueue, GPURenderBundle, GPURenderBundleEncoder, GPURenderPassEncoder, GPURenderPipeline, GPUSampler, GPUShaderModule, GPUShaderStage, GPUSupportedFeatures, GPUSupportedLimits, GPUTexture, GPUTextureUsage, GPUTextureView, GPUUncapturedErrorEvent, GPUValidationError, GravitySensor, Gyroscope, HashChangeEvent, Headers, HID, HIDConnectionEvent, HIDDevice, HIDInputReportEvent, Highlight, HighlightRegistry, history, History, HTMLAllCollection, HTMLAnchorElement, HTMLAreaElement, HTMLAudioElement, HTMLBaseElement, HTMLBodyElement, HTMLBRElement, HTMLButtonElement, HTMLCanvasElement, HTMLCollection, HTMLDataElement, HTMLDataListElement, HTMLDetailsElement, HTMLDialogElement, HTMLDirectoryElement, HTMLDivElement, HTMLDListElement, HTMLDocument, HTMLElement, HTMLEmbedElement, HTMLFencedFrameElement, HTMLFieldSetElement, HTMLFontElement, HTMLFormControlsCollection, HTMLFormElement, HTMLFrameElement, HTMLFrameSetElement, HTMLHeadElement, HTMLHeadingElement, HTMLHRElement, HTMLHtmlElement, HTMLIFrameElement, HTMLImageElement, HTMLInputElement, HTMLLabelElement, HTMLLegendElement, HTMLLIElement, HTMLLinkElement, HTMLMapElement, HTMLMarqueeElement, HTMLMediaElement, HTMLMenuElement, HTMLMetaElement, HTMLMeterElement, HTMLModElement, HTMLObjectElement, HTMLOListElement, HTMLOptGroupElement, HTMLOptionElement, HTMLOptionsCollection, HTMLOutputElement, HTMLParagraphElement, HTMLParamElement, HTMLPictureElement, HTMLPreElement, HTMLProgressElement, HTMLQuoteElement, HTMLScriptElement, HTMLSelectedContentElement, HTMLSelectElement, HTMLSlotElement, HTMLSourceElement, HTMLSpanElement, HTMLStyleElement, HTMLTableCaptionElement, HTMLTableCellElement, HTMLTableColElement, HTMLTableElement, HTMLTableRowElement, HTMLTableSectionElement, HTMLTemplateElement, HTMLTextAreaElement, HTMLTimeElement, HTMLTitleElement, HTMLTrackElement, HTMLUListElement, HTMLUnknownElement, HTMLVideoElement, IDBCursor, IDBCursorWithValue, IDBDatabase, IDBFactory, IDBIndex, IDBKeyRange, IDBObjectStore, IDBOpenDBRequest, IDBRequest, IDBTransaction, IDBVersionChangeEvent, IdentityCredential, IdentityCredentialError, IdentityProvider, IdleDeadline, IdleDetector, IIRFilterNode, Image, ImageBitmap, ImageBitmapRenderingContext, ImageCapture, ImageData, ImageDecoder, ImageTrack, ImageTrackList, indexedDB, Ink, InputDeviceCapabilities, InputDeviceInfo, InputEvent, IntersectionObserver, IntersectionObserverEntry, isSecureContext, Keyboard, KeyboardEvent, KeyboardLayoutMap, KeyframeEffect, LargestContentfulPaint, LaunchParams, launchQueue, LaunchQueue, LayoutShift, LayoutShiftAttribution, LinearAccelerationSensor, localStorage, location, Location, locationbar, Lock, LockManager, matchMedia, MathMLElement, MediaCapabilities, MediaDeviceInfo, MediaDevices, MediaElementAudioSourceNode, MediaEncryptedEvent, MediaError, MediaKeyMessageEvent, MediaKeys, MediaKeySession, MediaKeyStatusMap, MediaKeySystemAccess, MediaList, MediaMetadata, MediaQueryList, MediaQueryListEvent, MediaRecorder, MediaSession, MediaSource, MediaSourceHandle, MediaStream, MediaStreamAudioDestinationNode, MediaStreamAudioSourceNode, MediaStreamEvent, MediaStreamTrack, MediaStreamTrackAudioStats, MediaStreamTrackEvent, MediaStreamTrackGenerator, MediaStreamTrackProcessor, MediaStreamTrackVideoStats, menubar, MessageChannel, MessageEvent, MessagePort, MIDIAccess, MIDIConnectionEvent, MIDIInput, MIDIInputMap, MIDIMessageEvent, MIDIOutput, MIDIOutputMap, MIDIPort, MimeType, MimeTypeArray, MouseEvent, moveBy, moveTo, MutationObserver, MutationRecord, NamedNodeMap, NavigateEvent, navigation, Navigation, NavigationActivation, NavigationCurrentEntryChangeEvent, NavigationDestination, NavigationHistoryEntry, NavigationPreloadManager, NavigationTransition, navigator, Navigator, NavigatorLogin, NavigatorManagedData, NavigatorUAData, NetworkInformation, Node, NodeFilter, NodeIterator, NodeList, Notification, NotRestoredReasonDetails, NotRestoredReasons, Observable, OfflineAudioCompletionEvent, OfflineAudioContext, offscreenBuffering, OffscreenCanvas, OffscreenCanvasRenderingContext2D, onabort, onafterprint, onanimationend, onanimationiteration, onanimationstart, onappinstalled, onauxclick, onbeforeinput, onbeforeinstallprompt, onbeforematch, onbeforeprint, onbeforetoggle, onbeforeunload, onbeforexrselect, onblur, oncancel, oncanplay, oncanplaythrough, onchange, onclick, onclose, oncommand, oncontentvisibilityautostatechange, oncontextlost, oncontextmenu, oncontextrestored, oncuechange, ondblclick, ondevicemotion, ondeviceorientation, ondeviceorientationabsolute, ondrag, ondragend, ondragenter, ondragleave, ondragover, ondragstart, ondrop, ondurationchange, onemptied, onended, onerror, onfocus, onformdata, ongotpointercapture, onhashchange, oninput, oninvalid, onkeydown, onkeypress, onkeyup, onlanguagechange, onload, onloadeddata, onloadedmetadata, onloadstart, onlostpointercapture, onmessage, onmessageerror, onmousedown, onmouseenter, onmouseleave, onmousemove, onmouseout, onmouseover, onmouseup, onmousewheel, onoffline, ononline, onpagehide, onpagereveal, onpageshow, onpageswap, onpause, onplay, onplaying, onpointercancel, onpointerdown, onpointerenter, onpointerleave, onpointermove, onpointerout, onpointerover, onpointerrawupdate, onpointerup, onpopstate, onprogress, onratechange, onrejectionhandled, onreset, onresize, onscroll, onscrollend, onscrollsnapchange, onscrollsnapchanging, onsearch, onsecuritypolicyviolation, onseeked, onseeking, onselect, onselectionchange, onselectstart, onslotchange, onstalled, onstorage, onsubmit, onsuspend, ontimeupdate, ontoggle, ontransitioncancel, ontransitionend, ontransitionrun, ontransitionstart, onunhandledrejection, onunload, onvolumechange, onwaiting, onwebkitanimationend, onwebkitanimationiteration, onwebkitanimationstart, onwebkittransitionend, onwheel, open, opener, Option, OrientationSensor, origin, originAgentCluster, OscillatorNode, OTPCredential, outerHeight, outerWidth, OverconstrainedError, PageRevealEvent, PageSwapEvent, PageTransitionEvent, pageXOffset, pageYOffset, PannerNode, parent, PasswordCredential, Path2D, PaymentAddress, PaymentManager, PaymentMethodChangeEvent, PaymentRequest, PaymentRequestUpdateEvent, PaymentResponse, performance, Performance, PerformanceElementTiming, PerformanceEntry, PerformanceEventTiming, PerformanceLongAnimationFrameTiming, PerformanceLongTaskTiming, PerformanceMark, PerformanceMeasure, PerformanceNavigation, PerformanceNavigationTiming, PerformanceObserver, PerformanceObserverEntryList, PerformancePaintTiming, PerformanceResourceTiming, PerformanceScriptTiming, PerformanceServerTiming, PerformanceTiming, PeriodicSyncManager, PeriodicWave, Permissions, PermissionStatus, personalbar, PictureInPictureEvent, PictureInPictureWindow, Plugin, PluginArray, PointerEvent, PopStateEvent, postMessage, Presentation, PresentationAvailability, PresentationConnection, PresentationConnectionAvailableEvent, PresentationConnectionCloseEvent, PresentationConnectionList, PresentationReceiver, PresentationRequest, PressureObserver, PressureRecord, print, ProcessingInstruction, Profiler, ProgressEvent, PromiseRejectionEvent, prompt, ProtectedAudience, PublicKeyCredential, PushManager, PushSubscription, PushSubscriptionOptions, queryLocalFonts, queueMicrotask, RadioNodeList, Range, ReadableByteStreamController, ReadableStream, ReadableStreamBYOBReader, ReadableStreamBYOBRequest, ReadableStreamDefaultController, ReadableStreamDefaultReader, RelativeOrientationSensor, releaseEvents, RemotePlayback, ReportBody, reportError, ReportingObserver, Request, requestAnimationFrame, requestIdleCallback, resizeBy, ResizeObserver, ResizeObserverEntry, ResizeObserverSize, resizeTo, Response, RestrictionTarget, RTCCertificate, RTCDataChannel, RTCDataChannelEvent, RTCDtlsTransport, RTCDTMFSender, RTCDTMFToneChangeEvent, RTCEncodedAudioFrame, RTCEncodedVideoFrame, RTCError, RTCErrorEvent, RTCIceCandidate, RTCIceTransport, RTCPeerConnection, RTCPeerConnectionIceErrorEvent, RTCPeerConnectionIceEvent, RTCRtpReceiver, RTCRtpSender, RTCRtpTransceiver, RTCSctpTransport, RTCSessionDescription, RTCStatsReport, RTCTrackEvent, scheduler, Scheduler, Scheduling, screen, Screen, ScreenDetailed, ScreenDetails, screenLeft, ScreenOrientation, screenTop, screenX, screenY, ScriptProcessorNode, scroll, scrollbars, scrollBy, ScrollTimeline, scrollTo, scrollX, scrollY, SecurityPolicyViolationEvent, Selection, self, Sensor, SensorErrorEvent, Serial, SerialPort, ServiceWorker, ServiceWorkerContainer, ServiceWorkerRegistration, sessionStorage, setInterval, setTimeout, ShadowRoot, SharedArrayBuffer, sharedStorage, SharedStorage, SharedStorageAppendMethod, SharedStorageClearMethod, SharedStorageDeleteMethod, SharedStorageModifierMethod, SharedStorageSetMethod, SharedStorageWorklet, SharedWorker, showDirectoryPicker, showOpenFilePicker, showSaveFilePicker, SnapEvent, SourceBuffer, SourceBufferList, speechSynthesis, SpeechSynthesis, SpeechSynthesisErrorEvent, SpeechSynthesisEvent, SpeechSynthesisUtterance, SpeechSynthesisVoice, StaticRange, status, statusbar, StereoPannerNode, stop, Storage, StorageBucket, StorageBucketManager, StorageEvent, StorageManager, structuredClone, styleMedia, StylePropertyMap, StylePropertyMapReadOnly, StyleSheet, StyleSheetList, SubmitEvent, Subscriber, SubtleCrypto, SuppressedError, SVGAElement, SVGAngle, SVGAnimatedAngle, SVGAnimatedBoolean, SVGAnimatedEnumeration, SVGAnimatedInteger, SVGAnimatedLength, SVGAnimatedLengthList, SVGAnimatedNumber, SVGAnimatedNumberList, SVGAnimatedPreserveAspectRatio, SVGAnimatedRect, SVGAnimatedString, SVGAnimatedTransformList, SVGAnimateElement, SVGAnimateMotionElement, SVGAnimateTransformElement, SVGAnimationElement, SVGCircleElement, SVGClipPathElement, SVGComponentTransferFunctionElement, SVGDefsElement, SVGDescElement, SVGElement, SVGEllipseElement, SVGFEBlendElement, SVGFEColorMatrixElement, SVGFEComponentTransferElement, SVGFECompositeElement, SVGFEConvolveMatrixElement, SVGFEDiffuseLightingElement, SVGFEDisplacementMapElement, SVGFEDistantLightElement, SVGFEDropShadowElement, SVGFEFloodElement, SVGFEFuncAElement, SVGFEFuncBElement, SVGFEFuncGElement, SVGFEFuncRElement, SVGFEGaussianBlurElement, SVGFEImageElement, SVGFEMergeElement, SVGFEMergeNodeElement, SVGFEMorphologyElement, SVGFEOffsetElement, SVGFEPointLightElement, SVGFESpecularLightingElement, SVGFESpotLightElement, SVGFETileElement, SVGFETurbulenceElement, SVGFilterElement, SVGForeignObjectElement, SVGGElement, SVGGeometryElement, SVGGradientElement, SVGGraphicsElement, SVGImageElement, SVGLength, SVGLengthList, SVGLinearGradientElement, SVGLineElement, SVGMarkerElement, SVGMaskElement, SVGMatrix, SVGMetadataElement, SVGMPathElement, SVGNumber, SVGNumberList, SVGPathElement, SVGPatternElement, SVGPoint, SVGPointList, SVGPolygonElement, SVGPolylineElement, SVGPreserveAspectRatio, SVGRadialGradientElement, SVGRect, SVGRectElement, SVGScriptElement, SVGSetElement, SVGStopElement, SVGStringList, SVGStyleElement, SVGSVGElement, SVGSwitchElement, SVGSymbolElement, SVGTextContentElement, SVGTextElement, SVGTextPathElement, SVGTextPositioningElement, SVGTitleElement, SVGTransform, SVGTransformList, SVGTSpanElement, SVGUnitTypes, SVGUseElement, SVGViewElement, SyncManager, TaskAttributionTiming, TaskController, TaskPriorityChangeEvent, TaskSignal, Text, TextDecoder, TextDecoderStream, TextEncoder, TextEncoderStream, TextEvent, TextFormat, TextFormatUpdateEvent, TextMetrics, TextTrack, TextTrackCue, TextTrackCueList, TextTrackList, TextUpdateEvent, TimeRanges, ToggleEvent, toolbar, top, Touch, TouchEvent, TouchList, TrackEvent, TransformStream, TransformStreamDefaultController, TransitionEvent, TreeWalker, TrustedHTML, TrustedScript, TrustedScriptURL, TrustedTypePolicy, TrustedTypePolicyFactory, trustedTypes, UIEvent, URL, URLPattern, URLSearchParams, USB, USBAlternateInterface, USBConfiguration, USBConnectionEvent, USBDevice, USBEndpoint, USBInterface, USBInTransferResult, USBIsochronousInTransferPacket, USBIsochronousInTransferResult, USBIsochronousOutTransferPacket, USBIsochronousOutTransferResult, USBOutTransferResult, UserActivation, ValidityState, VideoColorSpace, VideoDecoder, VideoEncoder, VideoFrame, VideoPlaybackQuality, ViewTimeline, ViewTransition, ViewTransitionTypeSet, VirtualKeyboard, VirtualKeyboardGeometryChangeEvent, VisibilityStateEntry, visualViewport, VisualViewport, VTTCue, WakeLock, WakeLockSentinel, WaveShaperNode, WebAssembly, WebGL2RenderingContext, WebGLActiveInfo, WebGLBuffer, WebGLContextEvent, WebGLFramebuffer, WebGLObject, WebGLProgram, WebGLQuery, WebGLRenderbuffer, WebGLRenderingContext, WebGLSampler, WebGLShader, WebGLShaderPrecisionFormat, WebGLSync, WebGLTexture, WebGLTransformFeedback, WebGLUniformLocation, WebGLVertexArrayObject, webkitCancelAnimationFrame, WebKitCSSMatrix, webkitMediaStream, WebKitMutationObserver, webkitRequestAnimationFrame, webkitRequestFileSystem, webkitResolveLocalFileSystemURL, webkitRTCPeerConnection, webkitSpeechGrammar, webkitSpeechGrammarList, webkitSpeechRecognition, webkitSpeechRecognitionError, webkitSpeechRecognitionEvent, webkitURL, WebSocket, WebSocketError, WebSocketStream, WebTransport, WebTransportBidirectionalStream, WebTransportDatagramDuplexStream, WebTransportError, WGSLLanguageFeatures, WheelEvent, window, Window, WindowControlsOverlay, WindowControlsOverlayGeometryChangeEvent, Worker, Worklet, WritableStream, WritableStreamDefaultController, WritableStreamDefaultWriter, XMLDocument, XMLHttpRequest, XMLHttpRequestEventTarget, XMLHttpRequestUpload, XMLSerializer, XPathEvaluator, XPathExpression, XPathResult, XRAnchor, XRAnchorSet, XRBoundedReferenceSpace, XRCamera, XRCPUDepthInformation, XRDepthInformation, XRDOMOverlayState, XRFrame, XRHand, XRHitTestResult, XRHitTestSource, XRInputSource, XRInputSourceArray, XRInputSourceEvent, XRInputSourcesChangeEvent, XRJointPose, XRJointSpace, XRLayer, XRLightEstimate, XRLightProbe, XRPose, XRRay, XRReferenceSpace, XRReferenceSpaceEvent, XRRenderState, XRRigidTransform, XRSession, XRSessionEvent, XRSpace, XRSystem, XRTransientInputHitTestResult, XRTransientInputHitTestSource, XRView, XRViewerPose, XRViewport, XRWebGLBinding, XRWebGLDepthInformation, XRWebGLLayer, XSLTProcessor
- "GlobalThisValue" is the Global Object defined in the ECMAScript specification.
- For review purposes, a "GlobalThisValue" is any of the following: `window`, `window.top`, `window.parent`, `window.frames`, `globalThis`, `self` (when `self` is at the top level of the global scope), or `this` (when `this` is at the top level of the global scope or in `eval()`).
- `document` is not a "GlobalThisValue", but the value of `defaultView` property is a "GlobalThisValue".
----------------------------------------------------------------
# Block Document CreateProcessingInstruction Analysis
## Code Review: Identify and Block document.createProcessingInstruction usage.

### What This Reviewer Flags
This reviewer identifies ALL usage of document.createProcessingInstruction. This API introduces XML injection and XSS vulnerabilities.

### What This Reviewer Looks For
Calls to document.createProcessingInstruction in all contexts: Loops, conditionals, event handlers, async callbacks, template literals, string concatenation, hidden by unicode escape sequences and Reflection APIs.

### Why It's Critical
Creates XML injection vulnerabilities enabling XSS attacks through stylesheet injection, data URIs, and CSP bypass.

### Safe Alternative
Remove the dangerous code. If stylesheet loading is needed, use `document.createElement('link')` and append to `document.head` in JavaScript. Do not add `<link>` to any refactored markup (not allowed).


----------------------------------------------------------------
# Block Document Event Handler Analysis

## Code Review: Identify and Block forbidden document event handler usage.

### Rule
Flag ONLY actual event handler registrations for these THREE forbidden events:
- rejectionhandled
- securitypolicyviolation
- unhandledrejection

### Correct Usage
1. Remove all forbidden event handlers.
2. Handle errors and rejections locally within the component scope.

### Instructions
1. Scan EVERY line for these patterns
2. All contexts: Loops, conditionals, event handlers, async callbacks, template literals, string concatenation, hidden by unicode escape sequences
3. Case-sensitive matching
4. Flag EVERY occurrence - no exceptions
5. Include the complete code context
6. Report ALL violations found

### Constraints
1. **Preserve Logic**: Maintain all other code logic. Do not remove any code that is not related to the forbidden event handlers.
2. **Complete Coverage**: Flag ALL instances of forbidden event handlers.



----------------------------------------------------------------
# Block Document Open

## Code Review: Identify and Block critical security issues with document.open usage.

### What This Reviewer Does
This reviewer examines JavaScript and TypeScript code to find ALL instances of `document.open` called with zero, one, or two arguments. These methods are inherently dangerous and represent critical security vulnerabilities that must be removed.

### What This Reviewer Flags
- `document.open()` with 0 args: BLOCKED - Clears document (security risk)
- `document.open(url)` with 1 arg: BLOCKED - Opens in same window (navigation hijacking)
- `document.open(url, name)` with 2 args: BLOCKED - Opens with target in same window (security risk)
- `document.open(url, name, features)` with 3+ args: ALLOWED

This reviewer detects direct calls, bracket notation (`document['open']`), destructuring (`const {open} = document`), and variable references in all contexts: Loops, conditionals, event handlers, async callbacks, template literals, string concatenation, hidden by unicode escape sequencesl

### Fix Recommendations
Replace with:
- `window.open(url, "_blank", "noopener,noreferrer")` for new windows
- DOM APIs (`createElement`, `appendChild`) for content manipulation
- Navigation APIs for routing



----------------------------------------------------------------
# Block Document Write

## Code Review: Identify and Block unsafe document.write and document.writeln usage.

### What This Reviewer Does
This reviewer examines JavaScript and TypeScript code to find ALL instances of `document.write` and `document.writeln`. These methods are inherently dangerous and represent critical security vulnerabilities that must be removed.

### What This Reviewer Flags
- **document.write()**: ALL uses - allows HTML injection enabling XSS attacks
- **document.writeln()**: ALL uses - identical to document.write with newline
- **Indirect calls**: Bracket notation (`document['write']`), destructuring (`const {write} = document`), aliasing
- **All contexts**: Loops, conditionals, event handlers, async callbacks, template literals, string concatenation, hidden by unicode escape sequences and Reflection APIs.

### Why Critical
These methods enable XSS attacks, can replace entire page content, block parsing, and violate LWS security policies. NO safe usage exists.

### Safe Alternatives
Use DOM APIs (`createElement`, `appendChild`), LWC templates, or `textContent` for user data.



----------------------------------------------------------------
# Block Direct Script Element Creation Analysis

## Code Review: Identify and Block direct script element creation.

### What This Reviewer Flags
This reviewer detects direct script element creation and manipulation that could enable XSS attacks or CSP bypasses.

### What This Reviewer Looks For
- `document.createElement('script')` or `new HTMLScriptElement()`
- Script injection via innerHTML/outerHTML/insertAdjacentHTML
- Setting script.src to dynamic/untrusted URLs, blob URLs, or data URLs
- Setting script.textContent, script.text, or script.innerHTML with code
- All contexts: Loops, conditionals, event handlers, async callbacks, template literals, string concatenation, hidden by unicode escape sequences

### Secure Alternative for Lightning Web Components
If the code contains a class that extends `LightningElement`, recommend using the platform's `loadScript` utility from `lightning/platformResourceLoader`.

### Examples
```js
// VIOLATION: Direct creation
const script = document.createElement('script');
script.src = untrustedUrl;

// VIOLATION: Setting textContent
script.textContent = userInput;

// VIOLATION: innerHTML injection
element.innerHTML = '<script>alert(1)</script>';

// VIOLATION: Blob URL
script.src = URL.createObjectURL(blob);

// SECURE (for Lightning Web Components): Use loadScript
import { loadScript } from 'lightning/platformResourceLoader';
await loadScript(this, LIBRARY_URL);
```



----------------------------------------------------------------
# Block eval

## Code Review: Identify and Block eval, Function, new Function and setInterval or setTimeout with a string.

### What This Reviewer Does
This reviewer examines Lightning Web Components and/or any JavaScript code to find all instances of eval, setInterval, setTimeout, Function, and new Function usage that represent critical security vulnerabilities.

### What This Reviewer Looks For
- **eval**: Any code sent to JavaScript eval function is unsafe, and should be avoided.
- **setInterval**: Any code evaluated via string argument is unsafe, and should be avoided.
- **setTimeout**: Any code evaluated via string argument is unsafe, and should be avoided.
- **Function**: Any code evaluated via string argument is unsafe, and should be avoided.
- **new Function**: Any code evaluated via string argument is unsafe, and should be avoided.

### Correct Usage
1. Occurrences of eval, Function, and new Function must be annotated with a comment warning against use.
2. Occurrences of setInterval, setTimeout that accept a string argument should be removed.

### Review Steps
1. **Identify Usage**: Check for occurrences of eval, setInterval, setTimeout, Function, and new Function in the code.
2. **Evaluate Safety**: Determine if usage is unsafe for LWS, according to the criteria above.

### Constraints
1. **Preserve Logic**: Maintain all other code logic. Do not remove any code that is not related to the issue.



----------------------------------------------------------------
# Block Event Properties

## Code Review: Identify and Block all event.originalTarget and event.explicitOriginalTarget usages.

### What This Reviewer Does
This reviewer examines JavaScript and TypeScript code to find ALL instances of forbidden event properties. It MUST report EVERY SINGLE occurrence of `event.originalTarget` and `event.explicitOriginalTarget`.

### What This Reviewer Looks For

**Forbidden Event Properties** (always flag):
- `event.originalTarget`
- `event.explicitOriginalTarget`
- `Event.prototype.originalTarget`
- `Event.prototype.explicitOriginalTarget`

### Why This Matters

These properties bypass Lightning Web Security's shadow DOM isolation and expose elements outside the component's security boundary.

### Review Steps

1. **Scan for direct access**: Find all `event.originalTarget` and `event.explicitOriginalTarget` usage
2. **Check prototype modifications**: Find modifications to Event.prototype
3. **Flag all instances**: Every occurrence is a violation

### Output Format

For each issue found:
- **Suggested Action**: Use `event.target` or `event.currentTarget` instead

### Constraints

1. **Complete coverage**: Return EVERY instance found in the code

### Important Notes

- There are NO exceptions for these forbidden properties
- ALL instances must be flagged regardless of context



----------------------------------------------------------------
# Block Fullscreen API

## Code Review: Identify and Block requestFullscreen and vendor prefixed versions usage.

### What This Reviewer Does
This reviewer examines Lightning Web Components and/or any JavaScript or TypeScript code to find all instances of requestFullscreen() method invocations. Only requestFullscreen and its vendor-prefixed variants are violations.

### What This Reviewer Looks For

#### Critical Security Issues - Fullscreen API Invocations

**Methods** (always flag):
- `requestFullscreen()` - Standard method
- `webkitRequestFullscreen()` - WebKit prefix
- `mozRequestFullScreen()` - Mozilla prefix (capital 'S' in 'Screen')
- `msRequestFullscreen()` - Microsoft prefix

### Key Considerations
- **Fullscreen API**: Any usage of Fullscreen API method - requestFullscreen as well as vendor prefixed versions - is unsafe and can be exploited for phishing attacks by hiding browser security indicators.
- **All variants**: This includes all browser-prefixed versions (webkit, moz) and all access patterns (direct, dynamic, stored references).
- **Case sensitivity**: Pay special attention to mozRequestFullScreen (capital 'S' in 'Screen') vs other variants.
- **String property access**: Pay special attention to string properties that contain the word 'fullscreen' as well as the word 'screen', it can act as a backdoor entry point for phishing attacks.

### Correct Usage
1. Remove all requestFullscreen and vendor prefixed versions usage from Lightning Web Components and/or any JavaScript code.
2. Do not implement fullscreen functionality due to security risks.

### Review Steps
1. All occurrences of requestFullscreen is a violation.

### Constraints
1. **Preserve Logic**: Maintain all other code logic. Do not remove any code that is not related to the requestFullscreen and vendor prefixed versions.



----------------------------------------------------------------
# Block Global Object Property Assignment Analysis

## Code Review: Identify and Block all direct property assignments to global objects.

**CRITICAL PREREQUISITE:**
- ONLY analyze module code (a file with at least one import and/or export statement)
- If a file is not module code (no imports and no exports), DO NOT flag ANY issues in that file
- **IMPORTANT:** If a file has NO import or export statements at all, it should be skipped entirely
- **WARNING:** Even if you find obvious GlobalThisValue assignments like `globalThis.property = value`, you MUST ignore them if the file is not module code
- This rule applies to the ENTIRE file - if the file is not module code, skip the file entirely

### Review Steps
1. **STEP 1 - Module Check (MANDATORY):**
   - Search the entire file for any import or export declarations

   **DECISION POINT:**
   - If an import or export is found → Continue to Step 2
   - If NO import or export declarations are found → Return empty list (no issues). DO NOT CONTINUE TO STEP 2.

2. **STEP 2 - Global Object Analysis (only if Step 1 passed):**
  - Find all JavaScript code that directly assigns properties to global objects. Look for patterns like:
    - `globalThis.propertyName = value`
    - `window.propertyName = value`
    - `window.top.propertyName = value`
    - `window.parent.propertyName = value`
    - `window.frames.propertyName = value`
    - `document.defaultView.propertyName = value`
    - `self.propertyName = value` (when self refers to the global object)
    - `this.propertyName = value` (when this refers to the global object in global scope, or at the top level)
3. Do NOT flag:
  - Property access (reading): `const x = window.location`
  - Local assignments: `function foo(window) { window.localVar = 1 }`
  - Method calls: `window.alert('hello')`
  - Host objects (like document etc.) EXCEPT when they are used as global object references
4. IMPORTANT:
  - NEVER flag Built-in objects (like Set, Map, Array, etc.)
  - NEVER flag Host objects (like document etc.) EXCEPT when they are used as global object references
  - Global object references that should be flagged: globalThis, window, window.top, window.parent, window.frames, document.defaultView, self (global), this (global)


### Examples
**Examples of what to FLAG:**
```javascript
globalThis.myVar = 'hello';
window.config = { debug: true };
window.top.config = { debug: true };
window.parent.config = { debug: true };
window.frames.config = { debug: true };
self.data = [];
this.globalFunction = function() {};
document.defaultView.property = value;
globalThis.foo += 1;
window.bar -= 5;
```

**Examples of what to IGNORE:**
```javascript
const x = window.location; // reading, not assigning
function foo(window) { window.local = 1; } // local parameter
window.alert('hello'); // method call, not assignment
const config = window.config; // reading
document.cookie = 'foo=bar'; // DO NOT FLAG - document is not in the flagged list
localStorage.setItem('key', 'value'); // DO NOT FLAG - localStorage is not in the flagged list
document.foo = 1; // DO NOT FLAG - document is not in the flagged list
```

When reviewing code, include ALL VIOLATIONS. Do not omit any.

### Constraints
1. **Module Code Required**: Only analyze module code (files with at least one import and/or export statement)
2. **Preserve Logic**: Maintain all other code logic.
3. ONLY report issues that are related to the instructions.
4. Properties of other objects are not considered "global objects" references.
5. Violations of the rules are considered security issues.

### Final Validation
Before returning any issues, ask yourself:
1. Is this file module code? (Check for any import or export statements)
2. If NO → Return empty list
3. If YES → Return the issues found

**Remember:** Not module code = No issues to report, regardless of what global object assignments you find.



----------------------------------------------------------------
# Block HTML Body Element Event Analysis

## Code Review: Identify and Block use of document.body event handlers that leak sensitive information

### What This Reviewer Does
This reviewer finds document.body event handler usage that creates security vulnerabilities by exposing promise rejections, storage events, navigation state, and enabling user tracking.

### What This Reviewer Detects
- `document.body.addEventListener(...)` and `document.body.oneventname = ...` assignments
- Destructured references: `const { body } = document;` then `body.addEventListener` or `body.oneventname`
- Bracket notation: `document.body['on' + var]` or `body[eventName]`
- Unicode escapes: `document.body['\u006f\u006e...']`
- Reflect patterns: `Reflect.set(document.body, 'onevent', ...)` or `Reflect.apply(document.body.addEventListener, ...)`
- String concatenation for event names

### What This Reviewer Reports
This reviewer flags only the **actual handler assignment line**, not intermediate variable construction. It reports ALL occurrences case-sensitively.



----------------------------------------------------------------
# Block Nonce Access Analysis
## Code Review: Identify and Block nonce value access violations (CSP enforcement)

### What This Reviewer Does
This reviewer identifies ALL attempts to access nonce values on HTMLElement/SVGElement objects. Nonce access enables CSP bypass attacks.

### Core Rule
Nonces are cryptographic tokens for Content-Security-Policy and must NEVER be readable from client-side JavaScript.

### What This Reviewer Looks For
- **Direct access**: `element.nonce`, `element['nonce']`
- **getAttribute methods**: `.getAttribute('nonce')`, `.getAttributeNode('nonce')`
- **Selectors**: `querySelector('[nonce]')`, `querySelectorAll('script[nonce]')`
- **Variable-based**: `element[prop]`, `getAttribute(attrName)`, string concat/templates
- **Storage**: `localStorage/sessionStorage.setItem()` with nonce values
- **Setting**: `element.nonce = value`, `setAttribute('nonce', value)`
- **Loops**: `forEach`, `map`, `for...of` accessing nonce
- **Destructuring**: `const { nonce } = element`
- **Conditionals**: `if (element.nonce)`, `element.nonce || default`

### Why It Matters
Stolen nonces allow attackers to inject unauthorized scripts that bypass CSP, enabling XSS attacks.

### Correct Approach
If the code contains a class that extends `LightningElement`, use `loadScript`/`loadStyle` from `lightning/platformResourceLoader`. Never access, store, or transmit nonce values.


----------------------------------------------------------------
# Block UIEvent Range Parent Analysis

## Code Review: Identify and Block UIEvent Range Parent Access

### What This Reviewer Does
This reviewer finds all instances where code accesses the `rangeParent` property from event objects. This includes direct access (event.rangeParent), chained access (event.target.rangeParent), destructuring, and obfuscated patterns using unicode escapes, bracket notation, or Reflect APIs.

### Fix
Replace with event.target or event.currentTarget instead.

### Response Formatting
Refer to code using inline single backticks only. Do NOT use fenced code blocks (triple backticks) anywhere in the response, including within reasoning or explanation fields. Fenced code blocks corrupt the JSON response format.



----------------------------------------------------------------
# Block Worker Family Globals Analysis

## Code Review: Block Worker-Family Globals (Worker, SharedWorker, ServiceWorker).

### What This Reviewer Does
This reviewer examines Lightning Web Components and/or any JavaScript or TypeScript code to find every use of the worker-family browser globals. Lightning Web Security (LWS) makes these globals unavailable at runtime, so any use is a violation. Even though `Worker`, `SharedWorker`, `ServiceWorker`, and `navigator` are recognized host identifiers, that only means the names resolve; it does NOT mean they are usable. Every construction, registration, and access is flagged.

### What This Reviewer Looks For

#### Dedicated Workers (always flag)
- `new Worker(url)` and `new Worker(url, options)` - direct construction.
- Stored or aliased constructors: `const W = Worker; new W(url)`, `new window.Worker(url)`, `new self.Worker(url)`.
- Indirect construction: `window['Worker']`, `Reflect.construct(Worker, args)`, or names assembled by concatenation such as `'Wor' + 'ker'`.

#### Shared Workers (always flag)
- `new SharedWorker(url)` and `new SharedWorker(url, options)`.
- The same stored, aliased, bracket, `Reflect.construct`, and obfuscated patterns as above applied to `SharedWorker`.

#### Service Workers (always flag)
- `navigator.serviceWorker.register(...)` and any call on the container: `getRegistration`, `getRegistrations`, `.ready`, `.controller`, `.addEventListener`.
- Reads of the `navigator.serviceWorker` getter itself, including feature detection like `if ('serviceWorker' in navigator)` or `if (navigator.serviceWorker)`.
- Aliased navigator access: `const nav = navigator; nav.serviceWorker.register(...)`, and obfuscated property names such as `navigator[['service','Worker'].join('')]`.

### Runtime Behavior Under LWS
- `new Worker(...)` - the constructor throws `LockerSecurityError` ("Cannot create Worker ..."). It does not silently return undefined.
- `new SharedWorker(...)` - the constructor throws `LockerSecurityError` where the browser supports SharedWorker.
- `navigator.serviceWorker` - the getter returns `undefined` (the read itself does not throw).
- `navigator.serviceWorker.register(...)` - throws synchronously (a `TypeError`, because `navigator.serviceWorker` is `undefined`); it is NOT a rejected promise. The `ServiceWorkerContainer` prototype is additionally a revoked proxy.

### Why LWS Blocks These
- A `Worker` runs a separate top-level script on its own thread OUTSIDE the LWS near-membrane sandbox, so its code would run undistorted and defeat per-namespace isolation.
- A `SharedWorker` adds a shared, un-sandboxed channel reachable by multiple browsing contexts on the same origin, bridging data across namespaces.
- A service worker is a persistent, origin-scoped background script that intercepts network requests and controls the HTTP cache for the whole origin, enabling request interception and cache poisoning across namespaces.

### Recommended Platform Alternatives
- Heavy or background computation - move it to the server with Apex (`@salesforce/apex`, imperative or `@wire`).
- Data access and client caching - use Lightning Data Service and UI API wire adapters (`getRecord`, GraphQL wire adapter).
- Async server-to-client push (the service-worker/push use case) - use Platform Events via `lightning/empApi`.
- Cross-context or cross-component messaging (the shared-worker use case) - use Lightning Message Service (`lightning/messageService`) or standard LWC events.
- Loading a third-party library - package it as a static resource and load it on the main thread with `loadScript` from `lightning/platformResourceLoader`.

### Output Format
- **Type**: "Unavailable Worker-Family Global: [symbol]" where [symbol] is Worker, SharedWorker, ServiceWorker, or navigator.serviceWorker.
- **Location**: Line and column numbers.
- **Code**: The specific offending line.
- **Description**: State that the global is unavailable under LWS and describe the runtime behavior (constructor throws, or getter returns undefined).
- **Intent Analysis**: What the developer was trying to accomplish.
- **Suggested Action**: The specific platform alternative that fits the intent.

### Key Rules
1. Flag ALL instances - no exceptions, in both JavaScript and HTML.
2. Detect stored, aliased, bracket, `Reflect.construct`, and string-concatenation obfuscation of the global names.
3. Flag reads of the `navigator.serviceWorker` getter even without a following method call.
4. Preserve all unrelated code logic; only the worker-family usage is a violation.
5. Return an empty array if there are no issues.



----------------------------------------------------------------
# Block XSLTProcessor Analysis

## Code Review: Identify and Block all XSLTProcessor API usage.

### What This Reviewer Does
This reviewer finds ALL instances of `XSLTProcessor`, `transformToFragment`, and `transformToDocument`. These APIs enable XSS attacks and bypass security controls.


### What This Reviewer Looks For
- `new XSLTProcessor()` - direct instantiation
- `window.XSLTProcessor` or `const P = XSLTProcessor` - indirect references
- `Reflect.construct(XSLTProcessor, [])` - reflection-based instantiation
- `transformToFragment()` and `transformToDocument()` - transformation methods
- `processor['transformToFragment']` - bracket notation
- `Reflect.apply()`, `.apply()`, `.call()`, `.bind()` - reflection-based method calls

### Why This Matters
XSLT transformations can generate `<script>` tags, event handlers, and bypass CSP. There is NO safe usage.

### Safe Alternatives
1. If the code contains a class that extends `LightningElement`, use LWC templates with data binding
2. Process XML on server-side with Apex
3. Use JSON instead of XML
4. Use DOM APIs (`createElement`, `appendChild`) with proper escaping

### Output Format



----------------------------------------------------------------
# Block Context Vulnerability Access Analysis

## Code Review: Identify and Block context vulnerability attacks.

### What This Reviewer Flags
This reviewer flags security vulnerabilities where **imported framework classes** are exploited through context manipulation: bind(), call(), apply(), Reflect methods, prototype manipulation, and framework element access.

**CRITICAL**: Imported modules expose framework internals. Static resources via loadScript() are safe.

### What This Reviewer Looks For

1. **Method Context Manipulation**: .call(), .apply(), .bind(), Reflect.apply() on imported methods with external context
2. **Crafted Fake Context**: Objects mimicking framework structures passed to framework methods
3. **Component Extension**: Extending imported framework components to access inherited internals
4. **Prototype Manipulation**: __lookupSetter__(), __lookupGetter__(), Object.getPrototypeOf(), Object.setPrototypeOf()
5. **Internal Property Access**: .helper, .context, .owner, .navService on DOM elements/components
6. **Hierarchy Traversal**: getOwner(), getContext() calls or loops traversing object hierarchies
7. **Dynamic Creation with Exploited Context**: Using stolen contexts for component creation
8. **Complex Invocation Chains**: Function.prototype.call.apply() or Function.prototype.apply.call()
9. **All contexts**: Loops, conditionals, event handlers, async callbacks, template literals, string concatenation, hidden by unicode escape sequences

### What This Reviewer Ignores
- Standard LWC lifecycle methods
- Event handlers with proper this binding within same component
- Built-in JavaScript methods without external context manipulation
- Code loaded via loadScript() from static resources

### Attack Patterns

**CustomEvent Context Claiming**
```javascript
// BAD: Intercepting framework context via CustomEvent
let evt = new CustomEvent(frameworkEventName, {
  detail: {
    callback: function(ctx) {
      while (true) {
        let root = ctx.getOwner();
        if (root === ctx) break;
        ctx = root;
      }
      ctx.helper.someMethod.call({ initService: { property: document } }, data);
    }
  }
});
```

**Component Extension + Prototype**
```javascript
// BAD: Extending imported component with prototype manipulation
import ImportedComponent from 'framework/componentName';
export default class extends ImportedComponent {
  renderedCallback() {
    this.__lookupSetter__('prop').call(fakeContext, payload);
  }
}
```

**Framework Access + Traversal**
```javascript
// BAD: Accessing internal elements and traversing context
let element = document.querySelector('framework-internal-element');
let ctx = element.internalService.context;
while (ctx.getOwner() !== ctx) ctx = ctx.getOwner();
```

### Correct Usage
1. Never access internal properties (.helper, .context, .owner, .navService)
2. Never traverse hierarchies (getOwner(), getContext())
3. Only query within template: this.template.querySelector()
4. Never extend imported framework components
5. Never use context manipulation on imported objects with external contexts



----------------------------------------------------------------
# Block Critical Node Mutation Analysis

## Code Review: Identify and Block structural mutation of critical (shared) DOM nodes.

### Objective
Examine Lightning Web Components and any JavaScript or TypeScript code for structural DOM mutations that target a **critical (shared) node**. Lightning Web Security protects a small set of top-of-document nodes that every component on the page shares. Flag any attempt to insert, remove, or replace the children of those nodes, because doing so lets one component tamper with the shell the whole page depends on.

### What Counts as a Critical (Shared) Node
Under Lightning Web Security the shared nodes are ONLY:
- the top-level `document` itself (`document`, `window.document`)
- the root element `document.documentElement` (the `<html>` element)
- `document.head`
- `document.body`

References resolved through aliases still count, e.g. `const { body, head } = document;`, `const root = document.documentElement;`, `const d = window.document;`.

### What to Flag
Flag these DOM-mutation calls **when the receiver (or, for removals/replacements, the child being removed or replaced) is a critical/shared node**:
- **replaceChildren**: `document.body.replaceChildren(...)`, `document.head.replaceChildren(...)`, `document.documentElement.replaceChildren(...)`, `document.replaceChildren(...)`
- **Child insertion**: `appendChild`, `insertBefore`, and the `Element` insertion helpers `append`, `prepend`, `before`, `after`, `insertAdjacentElement`, `insertAdjacentHTML`
- **Child removal**: `removeChild(criticalNode)`, `remove()` called on a critical node
- **Child replacement**: `replaceChild(newNode, criticalNode)`, `replaceWith(...)` called on a critical node
- **Aliased / dynamic forms**: destructured references (`const { body } = document`), bracket notation (`document['body'].append(...)`), and the same calls inside loops, conditionals, event handlers, async callbacks, or reached through `Reflect.apply`.

### What to Ignore
- **Component-owned nodes.** The same methods are safe on nodes the component owns: elements from `this.template.querySelector(...)`, `this.refs`, `this.querySelector(...)`, `document.createElement(...)`, document fragments, or any element that is NOT `document`/`documentElement`/`head`/`body`. Do NOT flag structural mutation of ordinary component-owned elements — `createElement`, `appendChild`, `removeChild`, and `textContent` on those nodes are the recommended, safe pattern.
- **Nodes in another document** (e.g. an iframe's `contentDocument`, a `DOMParser` document, or a detached `document.implementation.createHTMLDocument()` document). Only the top-level page's shared nodes are protected.
- Comments in code (analyze the actual code logic, not comments).

### Runtime Behavior Under LWS
Most of these mutations are intercepted by Lightning Web Security and throw a `LockerSecurityError` (an `Error` whose message is prefixed with `"Lightning Web Security: "`) synchronously, before the native operation runs. For example:
- `document.body.append(div)` → `"Cannot append DIV to BODY."`
- `document.head.replaceChildren()` → `"Cannot replace children of HEAD."`
- `document.replaceChildren()` → `"Cannot replace children of document."`
- `node.removeChild(document.body)` → `"Cannot remove BODY."`
- `document.documentElement.insertBefore(div, ref)` → `"Cannot insert child DIV into HTML,"`

The insertion helpers (`append`, `prepend`, `before`, `after`, `insertBefore`, `insertAdjacentElement`, `insertAdjacentHTML`) allow ONLY `<link>`, `<script>`, and `<style>` children on shared nodes; anything else throws. `replaceChildren`, `replaceWith`, `remove`, `removeChild`, and `replaceChild` throw unconditionally for a shared node.

Note on `appendChild`: the runtime distortion for `Node.prototype.appendChild` is currently deferred, so appending directly via `appendChild` may not throw today. It remains the same prohibited class of mutation and is enforced by its sibling APIs; relying on it is fragile and must still be flagged and fixed.

### Why LWS Blocks This
The document shell (`<html>`, `<head>`, `<body>`, and `document`) is shared across every component and namespace on the page. Allowing one component to restructure it enables:
1. **Cross-component tampering**: removing or replacing shared nodes breaks other components and the platform chrome.
2. **UI redress / clickjacking**: injecting content into `<body>` or `<html>` can overlay or spoof trusted UI.
3. **Persisted injection**: writing into `<head>` can smuggle in styles or resources that outlive the component.
4. **Denial of service**: `replaceChildren`/`remove` on the shell can wipe out the page.

### Recommended Platform Alternatives
- Confine DOM changes to the component's own subtree: query with `this.template` / `this.refs`, build nodes with `document.createElement`, and `appendChild`/`removeChild` **on those component-owned nodes**.
- Render dynamic content through the LWC template and reactive properties instead of mutating the document shell.
- To load a stylesheet or script, use `lightning/platformResourceLoader` (`loadStyle`/`loadScript`) rather than appending `<link>`/`<script>` to `<head>` yourself.

### Example of Unsafe Code
```js
import { LightningElement } from 'lwc';

export default class UnsafeComponent extends LightningElement {
  connectedCallback() {
    const banner = document.createElement('div');

    // UNSAFE: structural mutation of shared/critical nodes
    document.body.appendChild(banner);
    document.body.append(banner);
    document.head.replaceChildren();
    document.replaceChildren();

    const { body } = document;
    body.removeChild(body.firstElementChild);
    document.documentElement.insertBefore(banner, document.body);
  }
}
```

### Example of Safe Code
```js
import { LightningElement } from 'lwc';

export default class SafeComponent extends LightningElement {
  renderContent() {
    // SAFE: the same operations on component-owned nodes
    const container = this.template.querySelector('.container');
    const banner = document.createElement('div');

    container.appendChild(banner);
    container.replaceChildren(banner);
    container.removeChild(container.firstElementChild);
  }
}
```

### Output Format
- **Type**: "Critical Node Structural Mutation".
- **Location**: Line and column numbers of the offending call.
- **Code**: The specific offending line.
- **Description**: Name the shared node targeted and the runtime behavior (throws `LockerSecurityError`, or — for `appendChild` — is the same prohibited mutation class though its distortion is currently deferred).
- **Intent Analysis**: What the developer was trying to accomplish.
- **Suggested Action**: The component-owned-node or platform alternative that fits the intent.

### Key Rules
1. Flag a mutation only when the receiver (or, for removals/replacements, the removed/replaced child) resolves to `document`, `document.documentElement`, `document.head`, or `document.body` — including through aliases.
2. Do NOT flag the same methods on component-owned nodes (`this.template`, `this.refs`, `createElement` results, fragments); that is the recommended safe pattern.
3. Do NOT flag mutations targeting nodes in another document (iframe `contentDocument`, `DOMParser`, detached documents).
4. Resolve aliased, destructured, and bracket-notation references before deciding.
5. Return an empty array if there are no issues.



----------------------------------------------------------------
# Block Insecure HTML Injection

## Code Review: Identify and Block insecure HTML injection through DOM sinks that could lead to security vulnerabilities.

### What This Reviewer Does
This reviewer examines Lightning Web Components and/or any JavaScript or TypeScript code for insecure HTML injection patterns through DOM sinks. It focuses on any usage where untrusted or dynamically constructed HTML content is assigned to DOM manipulation methods, regardless of whether it's on regular elements, shadowRoot, or document objects.

### What This Reviewer Looks For
- **innerHTML assignments**: Direct assignment of untrusted content to innerHTML (on any element, shadowRoot, or document)
- **outerHTML assignments**: Direct assignment of untrusted content to outerHTML
- **insertAdjacentHTML calls**: Using insertAdjacentHTML with untrusted content
- **setHTML/setHTMLUnsafe calls**: Using these methods with untrusted content
- **Dangerous content patterns**:
  - Strings containing iframe elements with srcdoc attributes
  - Strings containing script elements
  - Dynamic HTML construction from variables
- **textContent with HTML**: Setting textContent to content that contains HTML markup
- **Any pattern where user input or external data is directly inserted into DOM sinks without proper sanitization**

### What This Reviewer Ignores
- Safe DOM methods like createElement, appendChild, removeChild
- Proper use of textContent with plain text (no HTML)
- LWC template rendering and data binding
- Standard Lightning component usage
- Comments in code (the actual code logic is analyzed, not comments)

### Security Risks
DOM sinks that accept HTML content are dangerous because:
1. **XSS vulnerabilities**: Malicious scripts can be injected through HTML content
2. **DOM manipulation attacks**: Attackers can modify the DOM structure
3. **Data exfiltration**: Sensitive data can be accessed through injected scripts
4. **Session hijacking**: Attackers can steal authentication tokens
5. **iframe/script injection**: Particularly dangerous patterns that bypass some security measures

### Safe Alternatives
Instead of unsafe DOM sink assignments, recommend:
- Use createElement() and appendChild() for safe DOM manipulation
- Use textContent for plain text (never HTML)
- Use LWC's templating system for dynamic content
- Implement proper input validation and sanitization
- Use Trusted Types when available

### Example of Unsafe Code

```js
export default class UnsafeComponent extends LightningElement {
  connectedCallback() {
    const userInput = this.getUserInput(); // Could contain malicious HTML

    // All of these are UNSAFE:
    this.template.querySelector('div').innerHTML = userInput;
    this.template.querySelector('div').shadowRoot.innerHTML = userInput;

    const blob = new Blob(['alert(document.cookie)'], { type: 'application/json' });
    const math = document.createElementNS('http://www.w3.org/1998/Math/MathML', 'x');
    math.setHTMLUnsafe(
      `<style><!--</style><img src="--><mi><iframe srcdoc='<script src=${URL.createObjectURL(blob)}></script>'></iframe>"/>
    );
  }
}
```

### Example of Safe Code

```js
export default class SafeComponent extends LightningElement {
  connectedCallback() {
    const userInput = this.getUserInput();

    // SAFE approaches:
    const div = this.template.querySelector('div');
    const textNode = document.createTextNode(userInput);
    div.appendChild(textNode);

    // Or use textContent for plain text
    div.textContent = userInput;
  }
}
```

### Response Formatting
Refer to code using inline single backticks only. Do NOT use fenced code blocks (triple backticks) anywhere in the response, including within reasoning, explanation, or suggested-fix fields. Fenced code blocks corrupt the JSON response format.



----------------------------------------------------------------
# Restrict Document ExecCommand Analysis

## Code Review: Flag and Restrict Dangerous document.execCommand Usage

### What This Reviewer Does
This reviewer scans for dangerous `document.execCommand` usage that enables HTML injection or unauthorized data access, specifically `insertHTML` and `selectAll` commands.

### What This Reviewer Flags
This reviewer flags ONLY `insertHTML` and `selectAll` commands. All other commands are safe and ignored.

**Dangerous Commands:**
- `insertHTML` - Enables HTML injection and XSS attacks
- `selectAll` - Can expose sensitive content via clipboard manipulation

**Detection Patterns:**
- Direct calls: `document.execCommand('insertHTML', ...)`
- Variables: `document.execCommand(cmdVar, ...)` where cmdVar could be dangerous
- String concatenation: `'insert' + 'HTML'`
- Bracket notation: `document['execCommand']('selectAll')`
- Unicode escape sequences

### Secure Alternatives
**For insertHTML:**
- Use Selection API with `Range.insertNode()` and `document.createElement()`
- Use `textContent` for text insertion
- Sanitize HTML if HTML insertion is required

**For selectAll:**
- Use `window.getSelection().selectAllChildren(element)`
- Use `Range.selectNodeContents(element)`
- Use modern Clipboard API: `navigator.clipboard.writeText()`

### Response Formatting
Refer to code using inline single backticks only. Do NOT use fenced code blocks (triple backticks) anywhere in the response, including within reasoning, explanation, or suggested-fix fields. Fenced code blocks corrupt the JSON response format.



----------------------------------------------------------------
# Avoid Cross Component Object Assumptions Analysis

## Code Review: Avoid unsafe assumptions about objects that crossed a component or platform boundary.

### Background
Under Lightning Web Security (LWS), components run in isolated sandboxes. When an object travels from another component, from a parent, or from the platform into your component — through an `@api` property, an event `detail`, a wire response, a callback argument, `postMessage`, or a host API return value — what your code receives is a wrapped view of that object, not the original. The wrapper preserves the object's shape and behavior for ordinary use, but it does NOT preserve every guarantee a plain in-realm object would. Treat any value that originated outside this component as a "foreign" object and avoid code that depends on it being the same object the sender holds.

You do not need to know HOW the boundary is implemented. You only need to recognize code that will behave differently — or break — because the object came from across a boundary.

### What This Reviewer Flags
This reviewer flags code that makes unsafe assumptions about foreign objects: identity comparisons, `instanceof`/constructor/prototype-shape checks, treating a received reference as live and shared, passing non-cloneable values through cross-boundary APIs, and invoking author-defined methods or reaching into internals on a received instance.

### What This Reviewer Looks For

1. **Reference-identity comparisons across the boundary**
   - Comparing a foreign object with `===`/`!==` (or via `Set`/`Map` key lookups, `indexOf`, `includes`) and assuming identity is stable.
   - e.g. `if (event.target === this.savedNode)`, `mySet.has(payload.user)`, `this.cache.get(record)`.
   - **Why**: A foreign object may be presented to you through a different reference than the sender holds, so identity checks can return an unexpected result.
   - **Fix**: Compare by a stable primitive key you control (e.g. an `id`/`recordId`/`name` field), not by object reference.

2. **`instanceof`, `.constructor`, and prototype-shape checks on foreign objects**
   - `payload instanceof SomeClass`, `value.constructor === Array`, `Object.getPrototypeOf(received) === X`, `Object.prototype.toString.call(received)` used to branch logic.
   - **Why**: A foreign object's constructor/prototype may resolve to a different one than the sender's, so type-brand checks are unreliable across a boundary.
   - **Fix**: Feature-detect (check for the property/method you need) or use a stable discriminator field, instead of class-brand checks. `Array.isArray()` remains safe for arrays.

3. **Assuming a received object is a live, shared, two-way reference**
   - Holding a foreign object and expecting that mutating it (or reading it later) reflects, or is reflected by, the sender — `this.shared = event.detail.model; ... this.shared.count++ /* expecting the parent to see it */`.
   - **Why**: A received object is generally a point-in-time view; writes you make are not guaranteed to propagate back, and the sender's later changes are not guaranteed to appear.
   - **Fix**: Communicate changes explicitly (dispatch an event, call a documented `@api` method) instead of relying on a shared mutable reference. Snapshot what you need into component-owned state.

4. **Passing non-cloneable / non-serializable values across a boundary**
   - Sending functions, class instances, DOM nodes, `Map`/`Set`, `Date`-dependent live objects, or objects with methods/getters through cross-boundary channels: `CustomEvent` `detail`, `postMessage`, `BroadcastChannel.postMessage`, `@api` payloads, `structuredClone` of such values.
   - e.g. `this.dispatchEvent(new CustomEvent('x', { detail: { onDone: () => {...}, svc: new Service() } }))`, `channel.postMessage(domNode)`.
   - **Why**: Only plain, structured-cloneable data is guaranteed to survive a boundary crossing; behavior-bearing values may be dropped, throw, or arrive without their methods.
   - **Fix**: Pass plain data (ids, strings, numbers, plain objects/arrays). Expose behavior through documented APIs or events, not by shipping functions/instances.

5. **Calling author-defined methods or reaching into internals on a received instance**
   - Invoking custom methods, or reading private/internal fields, on an object received from another component — `event.detail.handler.process()`, `this.childRef.internalState`, accessing `#`-style or framework-internal properties on a foreign object.
   - **Why**: A foreign instance may expose data without its full author-defined behavior, and internal/private surfaces are not part of any boundary-safe contract.
   - **Fix**: Rely only on the documented public contract (public `@api` methods/properties, event payloads). Do not depend on custom methods or internals of objects you received from elsewhere.

### What This Reviewer Ignores
- Objects created and fully owned by THIS component (plain literals, locally constructed values, results of this component's own computation).
- Mutation of foreign objects — that is covered by the "Avoid Mutating Unknown Objects" review; this reviewer focuses on identity, type-brand, liveness, cloneability, and method/internal assumptions, not on whether a mutation is allowed.
- `Array.isArray()` checks, and feature/property existence checks (`'foo' in obj`, `obj?.foo`).
- Passing plain, serializable data across boundaries.
- Standard DOM operations on this component's own template nodes (`this.template.querySelector(...)`, `classList`, `setAttribute`, `dataset`).

### Correct Approach
- Compare foreign objects by a stable primitive key you own, never by reference identity.
- Branch on feature detection or a discriminator field, not on `instanceof`/constructor/prototype shape.
- Treat received objects as point-in-time snapshots; coordinate change through events or documented `@api`, not shared mutable references.
- Send only plain, structured-cloneable data across boundaries; expose behavior through APIs, not shipped functions or instances.
- Depend only on the documented public contract of objects received from other components.



----------------------------------------------------------------
# Avoid Map Object Misuse

## Code Review: Prevent Map and Set objects misuse.

### What This Reviewer Flags
This reviewer flags Map and Set misuse in any Lightning Web Component code, JavaScript code, or TypeScript code.

### What This Reviewer Looks For

#### Direct Property Access/Assignment (CRITICAL)
- Using bracket notation: `map[key]` or `set[index]`
- Assigning with brackets: `map[key] = value` or `set[index] = value`
- **Why**: Map/Set use internal data structures. Direct property access bypasses their API.
- **Fix**: Use `map.set(key, value)`, `map.get(key)`, `set.add(value)`, `set.has(value)`

#### Serialization Issues
- Using `JSON.stringify()` on Map or Set directly
- Passing Map/Set in decorators (e.g., `@wire`, `@track`)
- Sending Map/Set in event payloads or to child components
- **Why**: Map/Set cannot be serialized.
- **Fix**: Convert to serializable format - `Object.fromEntries(map)`, `Array.from(set)`

#### Prototype Modification (CRITICAL)
- Adding properties to `Map.prototype` or `Set.prototype`
- **Why**: Extremely dangerous, affects all instances globally.
- **Fix**: Create custom classes that extend Map/Set

### What This Reviewer Ignores
- DOM API usage
- Code unrelated to Map/Set misuse



----------------------------------------------------------------
# Avoid Mutating Unknown Objects Analysis

## Code Review: Prevent mutation of objects that don't belong to the component.

### What This Reviewer Flags
This reviewer flags instances where code mutates objects that don't belong to the component. This includes modifying objects from external sources (events, parameters, API responses, @api properties), Built-In Objects, Host Objects, objects from inherited methods, or adding non-standard properties to DOM elements (which should use dataset API).

### What This Reviewer Looks For
- **Event object mutations** (e.g., `event.detail.value = 'x'`, `event.target.customProp = true`)
- **Parameter mutations** (e.g., `processConfig(config) { config.newProp = 'value'; }`)
- **API response mutations** (e.g., `wireData.processed = true`, `response.items.customField = 123`)
- **Mutations to properties received via @api** (e.g., `this.recordData.processed = true` where recordData is from @api)
- **Non-standard properties on DOM elements** (e.g., `element.customProp = 123` - use dataset API instead)
- **Tracked property mutations** (e.g., mutating wire data or external objects after storing in @track)
- **Prototype/Host Object mutations** (e.g., `Array.prototype.custom = fn`, `document.foo = 'x'`)
- **Mutations to objects from inherited methods** (methods not defined in this component)

### What This Reviewer Ignores
- Objects created and owned by this component (not received from external sources)
- Standard DOM operations (e.g., createElement, appendChild, querySelector, innerHTML, textContent, classList)
- Standard event handling (e.g., addEventListener, removeEventListener)
- Mutations to cloned/copied objects (e.g., `const local = { ...external }; local.prop = 'x';`)

### Correct Approach
- **Clone before modifying** (e.g., `const local = { ...external };` or `structuredClone(data)`)
- **Return new objects** instead of mutating parameters
- **Use dataset API for DOM metadata** (e.g., `element.dataset.custom = '123'` or `element.setAttribute('data-custom', '123')`)



----------------------------------------------------------------
# Avoid Restricted Salesforce Globals Analysis

## Code Review: Avoid depending on Salesforce-proprietary framework globals that are restricted under LWS.

**CRITICAL PREREQUISITE:**
- ONLY analyze files that import from 'lwc' (a class that extends `LightningElement`, or any other import with the 'lwc' module specifier).
- If a file does NOT import from 'lwc', DO NOT flag ANY issues in that file.
- **IMPORTANT:** If a file has NO import statements at all, it should be skipped entirely.
- **WARNING:** Even if you find an obvious `$A`, `Aura`, `$Lightning`, or `Sfdc` reference, you MUST ignore it if there is no import from 'lwc'.
- This rule applies to the ENTIRE file — if there is no import from 'lwc', skip the file entirely.

### Review Steps
1. **STEP 1 — Import Check (MANDATORY):**
   - Search the entire file for any import declaration whose module specifier is 'lwc' (for example `import { LightningElement } from 'lwc';`).

   **DECISION POINT:**
   - If an import from 'lwc' is found → continue to Step 2.
   - If NO import from 'lwc' is found → return an empty list (no issues). DO NOT CONTINUE TO STEP 2.

2. **STEP 2 — Restricted Salesforce Global Analysis (only if Step 1 passed):**
   - Flag code that reaches for a Salesforce-proprietary framework global instead of a supported, importable platform API.

### Background
Lightning Web Security (LWS) runs component JavaScript inside an isolated sandbox with its own global object. The Salesforce-proprietary framework globals that legacy Aura and Lightning Out code reached for — `$A`, the `Aura` namespace, `$Lightning`, `Sfdc`/`sfdc`, and framework-internal handles such as `$A.lockerService` or the `$LWS` runtime — are NOT part of the surface a sandboxed component may depend on. They are either absent from the sandbox global, wrapped/distorted so they no longer behave as they did on a plain page, or reachable only by trusted platform code. Code that reads or calls them can work in an older Aura context or on an unsandboxed page yet be `undefined`, throw, or silently misbehave under LWS.

You do not need to know HOW LWS removes or distorts these globals. You only need to recognize code that depends on a Salesforce-proprietary framework global instead of a supported, importable platform API.

### My Job
I flag code inside an LWC module that reaches for a Salesforce-proprietary framework global rather than the supported, importable platform API. I focus on the proprietary framework surface (`$A`, `Aura`, `$Lightning`, `Sfdc`, `$A.lockerService`, `$LWS`), NOT on web-platform globals such as `window`, `navigator`, or `Worker`.

### What I Look For

1. **The Aura framework global `$A` (and `window.$A`, `window.Aura`, the bare `Aura` namespace)**
   - Any access to `$A` — `$A.get(...)`, `$A.enqueueAction(...)`, `$A.createComponent(...)`, `$A.getCallback(...)`, `$A.getReference(...)`, `$A.util.*`, `$A.reportError(...)`, `$A.log(...)` — or to the `Aura` / `window.Aura` namespace.
   - **Why**: `$A` is the Aura framework instance. It is not part of the LWS component sandbox surface, so a component cannot rely on it being present or behaving as it did in an Aura context.
   - **Fix**: Use the supported module for the task instead of `$A`:
     - Labels: `import LABEL from '@salesforce/label/...'` instead of `$A.get('$Label...')`.
     - Static resources: `import RES from '@salesforce/resourceUrl/...'` instead of `$A.get('$Resource...')`.
     - Server data / Apex: import Apex methods (`@salesforce/apex/...`) or use LDS wire adapters (`lightning/uiRecordApi`, GraphQL) instead of `$A.enqueueAction`.
     - Navigation: the `NavigationMixin` from `lightning/navigation` instead of `$A.get('e.force:navigate...')`.
     - Toasts: `ShowToastEvent` from `lightning/platformShowToastEvent` instead of `$A.get('e.force:showToast')`.
     - Cross-component events: Lightning Message Service (`lightning/messageService`), `CustomEvent`, or public `@api` instead of `$A.get('e.c:...')` application events.
     - Dynamic components: standard LWC composition or dynamic `import()` instead of `$A.createComponent`.

2. **The Lightning Out global `$Lightning`**
   - `$Lightning.use(...)`, `$Lightning.createComponent(...)`.
   - **Why**: `$Lightning` is the Lightning Out bootstrap global for embedding Aura apps in external pages. It is not a component-sandbox API and is not dependable from within an LWS-governed component.
   - **Fix**: Build the UI as first-class Lightning Web Components composed through the standard framework, rather than imperatively creating components through `$Lightning`.

3. **Internal Salesforce namespaces — `Sfdc` / `sfdc` / `Sfdc.*`**
   - Reading or calling anything under a global `Sfdc`/`sfdc` object (e.g. `Sfdc.canvas`, `window.Sfdc.userContext`).
   - **Why**: These are private, undocumented platform internals with no compatibility contract. LWS does not expose them to sandboxed components, and they may change or disappear without notice.
   - **Fix**: Do not depend on internal namespaces. Use a documented `@salesforce/*` scoped import (for example `@salesforce/user/Id`) or a `lightning/*` module for the capability you need.

4. **Framework-internal / Locker handles — `$A.lockerService`, `$LWS`, and similar**
   - `$A.lockerService.trusted.createScript(...)`, `$A.lockerService.restricted.createScript(...)`, or access to a `$LWS` / security-runtime global.
   - **Why**: These are trusted-platform internals — for example the code-signing surface used by framework code. Application and component code must not call them; they are not a supported extension point, and reaching for them is an attempt to access privileged internals.
   - **Fix**: Do not sign or evaluate code through framework internals. Load scripts and styles with `loadScript`/`loadStyle` from `lightning/platformResourceLoader`, and avoid dynamic evaluation entirely.

5. **Proprietary evaluation helpers — `aura.util.globalEval` / `$A.util.globalEval`**
   - `aura.util.globalEval(...)`, `$A.util.globalEval(...)`.
   - **Why**: This is a proprietary Aura evaluation helper. LWS distorts it, and using it to run source text is a dynamic-code-execution path that is both unavailable to and unsafe for sandboxed components.
   - **Fix**: Never evaluate source text. Use `loadScript` from `lightning/platformResourceLoader` for external libraries and normal module imports for code.

### What I Ignore
- Any file that does not import from 'lwc' (see the mandatory prerequisite above).
- Supported `@salesforce/*` scoped imports (`@salesforce/label/*`, `@salesforce/resourceUrl/*`, `@salesforce/apex/*`, `@salesforce/schema/*`, `@salesforce/user/*`, and similar) — these ARE the correct alternative and must NOT be flagged.
- Imports from `lightning/*` and `lwc` modules.
- Web-platform globals (`window`, `document`, `navigator`, `localStorage`, `Worker`, timers). Those are handled by other reviews; I only flag Salesforce-proprietary framework globals.
- A local variable, parameter, or property that merely happens to be named `aura`, `sfdc`, or similar but is not the proprietary global framework object (e.g. `const sfdc = buildConfig()` that never touches a proprietary global).
- Ordinary application logic, DOM work, and standard JavaScript.

### Correct Approach
- Reach capabilities through documented, importable APIs — `@salesforce/*` scoped imports and `lightning/*` modules — never through `$A`, `Aura`, `$Lightning`, or `Sfdc`.
- Treat any Salesforce-proprietary framework global as unavailable in the component sandbox: do not read it, call it, or feature-detect against it as a fallback.
- Do not reach for framework-internal or security-runtime handles (`$A.lockerService`, `$LWS`); they are trusted-platform-only.

### Final Validation
Before returning any issues, ask yourself:
1. Does this file import from 'lwc'? (Check for import statements.)
2. If NO → return an empty list.
3. If YES → return the issues found.

**Remember:** No import from 'lwc' = no issues to report, regardless of what Salesforce-proprietary globals appear in the file.



----------------------------------------------------------------
# Avoid Storage Scope Assumptions Analysis

## Code Review: Avoid assumptions about web storage scope and sharing.

### What This Reviewer Flags
This reviewer reviews any Lightning Web Component, JavaScript, or TypeScript code that uses web storage
(`localStorage`, `sessionStorage`, `document.cookie`) and flags code whose **correctness depends
on assumptions about how widely that storage is shared, how its keys are named, or how secret its
contents are**. It does not assume the code runs under Lightning Web Security (LWS); instead it advises
against assumptions that would silently break or leak if it does.

### Why this matters
When code runs inside an LWS sandbox, the web storage APIs keep their familiar shape — `getItem`,
`setItem`, `removeItem`, `key`, `length`, `document.cookie` — but the data is partitioned per
namespace. Each app gets its own isolated view: it cannot see, modify, or clear another namespace's
entries or a shared global store, and the keys it reads back may not be the literal strings it wrote.
This isolation protects a namespace from others; it does **not** encrypt the data or hide it from the
user. Code that assumes storage is a single global space, a cross-app message bus, an enumerable
key/value dump, or a secret vault can work in a plain browser yet behave differently — or expose
data — under LWS. The guidance below holds regardless of where the code actually runs.

### What This Reviewer Looks For

#### Cross-app / global sharing assumptions (CRITICAL)
- Treating `localStorage` as a cache or registry shared across different apps or components from
  other namespaces (e.g. writing in one app expecting another, unrelated app to read it back).
- **Why**: Under LWS each namespace sees an isolated partition, so the second reader gets nothing.
- **Advice**: Do not rely on storage to share state across namespace or app boundaries. Use an
  explicit, intended channel (a server, a documented API) for cross-app data.

#### Cross-context coordination via the `storage` event
- Using `window.addEventListener('storage', ...)` to coordinate or synchronize state between apps
  or tabs that may live in different namespaces.
- **Why**: Isolated partitions do not deliver each other's `storage` events, so the coordination
  silently never fires.
- **Advice**: Don't depend on `storage` events for cross-namespace messaging; use an explicit
  messaging mechanism.

#### Raw-key naming and enumeration assumptions
- Enumerating storage with `Object.keys(localStorage)`, `localStorage.key(i)`, or iterating
  `localStorage.length` and assuming the keys are exactly the literal strings that were written.
- Hand-constructing, parsing, or matching internal/prefixed key names rather than using the exact
  key string originally passed to `setItem`.
- **Why**: LWS may store entries under namespaced keys, so enumerated names can differ from what the
  code wrote, and cross-namespace entries are simply not visible.
- **Advice**: Read each value back with the same key string you wrote via `getItem`. Don't enumerate
  storage expecting a complete, raw, or globally shared key list, and don't depend on a key's internal
  on-disk representation.

#### Treating isolation as secrecy (CRITICAL)
- Storing secrets, auth tokens, API keys, or other sensitive data in `localStorage`,
  `sessionStorage`, or cookies on the assumption that sandbox isolation keeps them confidential.
- **Why**: Isolation separates one namespace from another; it is **not** encryption. Stored data
  stays cleartext-readable within its own namespace and by the user (e.g. via browser DevTools).
- **Advice**: Don't persist secrets in web storage. Keep sensitive material server-side or in a
  purpose-built secure mechanism; isolation is not confidentiality.

#### Cookie scope and persistence assumptions
- Writing or reading `document.cookie` while assuming the cookie is visible to, or shared with,
  other apps, domains, or namespaces, or assuming a particular persistence/scope.
- **Why**: Cookie visibility and scope can be partitioned per namespace under LWS, so a cookie set in
  one place may not be readable elsewhere.
- **Advice**: Don't rely on cookies for cross-app or cross-namespace sharing; treat cookie scope as
  local to the current context.

### What This Reviewer Ignores
- Ordinary namespace-local use: `setItem`/`getItem`/`removeItem` of a key the same code wrote and
  reads back, with no assumption about other apps, enumeration, or secrecy. This is correct and safe.
- Storing plainly non-sensitive UI state (e.g. a collapsed/expanded flag, a last-selected tab) for
  the current app's own later use.
- Code unrelated to web storage.



----------------------------------------------------------------
# Restrict Iframe Security Analysis

## Code Review: Flag and Restrict critical security issues with iframe usage.

### What This Reviewer Does
This reviewer examines code to detect insecure iframe usage that leads to XSS or mXSS attacks. It **BLOCKS all srcdoc usage** (bypasses CSP) and **RESTRICTS src to http/https only** (block javascript:, data:, blob:, file:, vbscript:, ftp:, etc.).

### Patterns This Reviewer Detects

```js
// BLOCKED: Any srcdoc usage
element.innerHTML = '<iframe srcdoc="<script>alert(1)</script>"></iframe>';
iframe.setAttribute('srcdoc', '<html>...</html>');

// BLOCKED: Dangerous protocols (not http/https)
iframe.src = 'javascript:alert(1)';
iframe.src = 'data:text/html,<script>alert(1)</script>';
iframe.src = URL.createObjectURL(blob);
iframe.src = 'vbscript:msgbox(1)';
iframe.src = 'file:///etc/passwd';

// BLOCKED: mXSS attacks (MathML/SVG/CDATA + srcdoc)
math.setHTMLUnsafe(`<style><!--</style><img src="--><mi><iframe srcdoc='...'></iframe>"/>`);
div.innerHTML = `<svg><desc><iframe srcdoc='<script>...</script>'></iframe></desc></svg>`;

// BLOCKED: Obfuscated protocols
iframe.src = '\u006a\u0061\u0076\u0061\u0073\u0063\u0072\u0069\u0070\u0074:alert(1)';
iframe.src = ('java' + 'script:') + 'alert(1)';

// ALLOWED: Only http/https
iframe.src = 'https://trusted-domain.com/content';
div.innerHTML = '<iframe src="https://example.com"></iframe>';
```

### How This Reviewer Works

- Scans for srcdoc in strings, setAttribute calls, template literals, and DOM sinks
- Scans iframe src for any protocol except http/https (including obfuscated variants)
- Detects mXSS contexts (MathML, SVG, CDATA) combined with iframe srcdoc
- Tracks variables, template literals, string concatenation, and unicode escape sequence patterns
- Returns detailed issue reports or an empty list if code is safe

### Response Formatting
Refer to code using inline single backticks only. Do NOT use fenced code blocks (triple backticks) anywhere in the response, including within reasoning, explanation, or suggested-fix fields. Fenced code blocks corrupt the JSON response format.



----------------------------------------------------------------
# Restrict Outbound Network Egress Analysis

## Code Review: Verify outbound network-egress targets (XMLHttpRequest and navigator.sendBeacon).

### Scope
This reviewer inspects any Lightning Web Component, JavaScript, or TypeScript code that sends an
outbound network request through `XMLHttpRequest` (`xhr.open(...)` / `xhr.send(...)`) or
`navigator.sendBeacon(...)`, and verifies that the destination URL is an approved endpoint. Any
request whose target is an external, third-party, protocol-relative, or dynamically built host is
flagged, because that is the shape of a data-exfiltration channel, and a structured Salesforce
alternative is recommended.

### Why this matters
`XMLHttpRequest` and `navigator.sendBeacon` keep working under Lightning Web Security (LWS), but LWS
does not itself decide whether a destination is trustworthy — sending component state, record data,
or session context to an unapproved host leaks it off-platform, and `sendBeacon` in particular fires a
fire-and-forget POST that is easy to overlook. Salesforce reaches external systems through declarative,
reviewable channels (Named Credentials with an Apex callout, hosts registered in CSP Trusted Sites /
Remote Site Settings) and reaches its own data through Apex (`@salesforce/apex/...`) and Lightning Data
Service (`lightning/uiRecordApi`, GraphQL wire). A raw browser request straight to a hardcoded
third-party domain, a protocol-relative URL, or a host assembled from a variable bypasses all of that
review. This guidance holds regardless of where the code actually runs.

### Approved targets (do NOT flag)
- Same-origin **relative** paths that begin with a single `/` (e.g. `/services/apexrest/MyService`,
  `/services/data/v59.0/query`) — these stay on the Salesforce origin.
- Relative paths with no scheme and no host (e.g. `./ping`, `telemetry`).

### Unapproved targets (ALWAYS flag)
- Absolute URLs to an external or third-party host (`https://collector.example.com/track`, any
  `http://` or `https://` host).
- **Protocol-relative** URLs that begin with `//` (e.g. `//analytics.example.com/x`) — these are
  cross-origin, NOT same-origin.
- URLs built dynamically from a variable, class field, function parameter, or template literal whose
  host cannot be verified from the code (e.g. `\`https://\${this.host}/api\``, `this.metricsUrl`).
- Any non-`http`/`https` scheme used as a request target.

### Where to Look
- `new XMLHttpRequest()` followed by `.open(method, url)` — the target is the 2nd argument to `open`;
  also inspect `.send(...)` for the data being transmitted.
- `navigator.sendBeacon(url, data)` — the target is the 1st argument.
- URLs held in variables, class fields, function parameters, string concatenation, and template
  literals that flow into either call.

### Output Format
- **Type**: "Unverified XHR Egress Target" or "Unverified sendBeacon Egress Target"
- **Location**: Line and column numbers
- **Code**: The specific line performing the request
- **Description**: Why the target is unverified and what data could leak
- **Intent Analysis**: What the developer intended
- **Suggested Action**: The structured alternative — an Apex callout behind a Named Credential (or a
  CSP Trusted Site) for external systems; Apex or Lightning Data Service for Salesforce data; or a
  same-origin relative path for a first-party endpoint.

### Key Rules
1. Evaluate variables, class fields, string literals, concatenations, and template literals that build
   the URL. A target you cannot resolve to an approved same-origin relative path is unverified — flag it.
2. Flag every unverified `XMLHttpRequest.open` target and every unverified `navigator.sendBeacon` target
   — no exceptions.
3. Treat a `//host` (protocol-relative) target as external, never as same-origin.
4. Do NOT flag requests whose target is an approved same-origin relative path (a single leading `/`, or
   no scheme and no host).
5. Detect obfuscation: `'htt' + 'ps://' + host`, template literals, and conditional URL assignment.
6. Return an empty list if there are no issues.
7. Do NOT embed Markdown code fences (```) in any reasoning or output field — reference code inline only.

### Out of Scope (do NOT flag)
- Requests to approved same-origin relative paths, as defined above.
- `fetch(...)` calls — outside the scope of this reviewer.
- Code that performs no outbound request via `XMLHttpRequest` or `navigator.sendBeacon`.



----------------------------------------------------------------
# Restrict Trusted Type Policy Analysis

## Code Review: Flag and Restrict use of forbidden Trusted Type Policy names.

### What This Reviewer Does
This reviewer examines Lightning Web Components and/or any JavaScript code to find all instances of `trustedTypes.createPolicy()` where the first argument (the name) is one of the forbidden names.

### What This Reviewer Looks For
Policy names that match any of these forbidden names must be renamed:
- **'default'**
- **'' (empty string)**
- **'lwsInternal'**
- **'trusted'**

### Correct Usage
1. Policy names must not match any of the forbidden names.
2. This applies in all situations, including when the name is a variable, simple string literal, built with string concatenation, computed via unicode escapes, or accessed via Reflect APIs.
3. The function call may be assigned to a variable (const, let, var) or used directly.

### Review Steps
1. **Identify Usage**: Check for all occurrences of `trustedTypes.createPolicy()` in the code.
2. **Evaluate Name**: Trace the first argument to determine its value, accounting for variables, string concatenation, array/object access, function returns, and Reflect APIs.
3. **Decode Unicode escape sequences** to determine intention.
4. **Match Against Forbidden Names**: Check if the resolved value matches any forbidden name.

### Constraints
1. **Preserve Logic**: Maintain all other code logic. Do not review the content of the policy (the second argument).
2. **Focus on Name**: Only review the policy name parameter.



----------------------------------------------------------------
# Restrict URL.createObjectURL Analysis

## Code Review: Flag and Restrict URL.createObjectURL usage.

### What This Reviewer Does
This reviewer examines code to identify uses of `URL.createObjectURL()` with restricted or unsupported MIME types. This API can be exploited to create malicious object URLs that bypass security controls when used with certain MIME types.

### Restricted MIME Types (Always Flag)
- `text/javascript` - CRITICAL: Blocked completely (if the code contains a class that extends `LightningElement`, use `loadScript` from `lightning/platformResourceLoader`)
- `text/html` - WARNING: Must be scanned for malicious content (script tags, XSS)
- `image/svg+xml` - WARNING: Can contain embedded JavaScript
- `text/xml` - WARNING: Must be scanned for malicious payloads
- Empty/undefined MIME types - Treated as text/plain but interpreted differently by browsers

### Where to Look
`URL.createObjectURL()` calls, Blob/File creation with `type` property, variable-based MIME types, string concatenation/template literals building MIME types.

### Output Format
- **Type**: "URL.createObjectURL with restricted/unsupported MIME type"
- **Severity**: "Critical" (text/javascript, empty types) or "Warning" (text/html, svg, xml)
- **Location**: Line and column numbers
- **MIME Type**: The specific restricted type
- **Code**: Specific line
- **Description**: Why it's restricted and security risks
- **Intent Analysis**: What developer intended
- **Suggested Action**: Use safe MIME types (image/png, video/mp4, application/pdf) or proper APIs (loadScript, DOMPurify)

### Key Rules
1. Evaluate all contexts, variable names, string literals, string concatenations, computed values, and unicode escapes
2. Flag ALL instances of restricted MIME types - no exceptions
3. Return empty array if no issues
4. Don't flag safe MIME types (image/*, video/*, audio/*, application/pdf)
5. Detect obfuscation: `'text/' + 'javascript'`, template literals, conditional assignments



----------------------------------------------------------------
# Restrict URL Schemes Analysis

## Code Review: Flag and Restrict disallowed URL schemes.

### What This Reviewer Does
This reviewer finds all URLs using a disallowed scheme. ONLY these three schemes are disallowed: `javascript:`, `vbscript:`, and `data:`. Every other scheme — including `http:`, `https:`, `about:blank`, `blob:`, `file:`, `ftp:`, `ws:`/`wss:`, `tel:`, `mailto:`, and custom app schemes — is allowed by this review and MUST NOT be flagged.

### Disallowed Schemes (Always Flag)
- `javascript:` - Arbitrary JavaScript execution, XSS attacks
- `vbscript:` - VBScript execution in legacy browsers
- `data:` - Bypasses CSP, can carry executable content (HTML, scripts, SVG)

### Allowed Schemes (Never Flag)
- `http:`, `https:`, `about:blank` - standard, safe navigation targets.
- `blob:`, `file:`, `ftp:`, `ws:`/`wss:`, `tel:`, `mailto:`, and any other custom or non-standard scheme - NOT flagged by this review. Do not report them here. (Blob URL creation is covered by a separate review.)

### Where to Look
HTML attributes (href, src, action), JavaScript strings/template literals, URL constructors, window.location/open, element.setAttribute, fetch/XHR URLs.

### Output Format
- **Type**: "Disallowed URL Scheme: [scheme]"
- **Location**: Line and column numbers
- **Code**: Specific line
- **Description**: Why it's a vulnerability
- **Intent Analysis**: What developer intended
- **Suggested Action**: Safe alternative using allowed schemes

### Key Rules
1. Case insensitive detection (JavaScript:, JAVASCRIPT:)
2. Flag ALL instances of `javascript:`, `vbscript:`, and `data:` - no exceptions
3. Never flag any other scheme - only these three are disallowed
4. Return empty array if no issues
5. Check both HTML templates and JavaScript
6. Detect obfuscation of the disallowed schemes, like `'java' + 'script:'` or splitting `'data'` + `':text/html'`



----------------------------------------------------------------
# Restrict SVGAnimateElement Attributes Analysis
## Code Review: Flag and Restrict use of URL values with SVGAnimateElements

### What This Reviewer Does
This reviewer identifies when SVGAnimateElement's `to`, `from`, or `values` attributes contain URL values like `url(...)`. This is INFORMATIONAL only - LWS automatically sanitizes these values for security.

### What to Flag
Flag ONLY when these patterns exist on SVGAnimateElement:
- `setAttribute('to', ...)` or `setAttribute('from', ...)` or `setAttribute('values', ...)` where the value contains `url(...)`
- Variable or template literal values that resolve to strings containing `url(...)`
- Return **empty array** if no URL patterns found in these attributes

### Critical Rules
1. **ONLY flag SVGAnimateElement**: The element must be created with `createElementNS('http://www.w3.org/2000/svg', 'animate')`
2. **ONLY these 3 attributes**: `to`, `from`, `values` - ignore all other attributes
3. **URL pattern required**: The attribute value must contain `url(...)` pattern
4. **Empty array if none found**: Return [] if no matches

### Examples to Flag
```javascript
const animate = document.createElementNS('http://www.w3.org/2000/svg', 'animate');
animate.setAttribute('to', 'url(#gradient)'); // FLAG: URL in 'to'
animate.setAttribute('from', 'url(#start)'); // FLAG: URL in 'from'
animate.setAttribute('values', 'url(#a); url(#b)'); // FLAG: URLs in 'values'
```

### Examples NOT to Flag
```javascript
const animate = document.createElementNS('http://www.w3.org/2000/svg', 'animate');
animate.setAttribute('dur', '3s'); // DON'T FLAG: no URL
animate.setAttribute('to', '#FF0000'); // DON'T FLAG: no url() pattern
```

### Response Formatting
Refer to code using inline single backticks only. Do NOT use fenced code blocks (triple backticks) anywhere in the response, including within reasoning, explanation, or suggested-fix fields. Fenced code blocks corrupt the JSON response format.


----------------------------------------------------------------
# Secure Range DOM Operations Analysis

## Code Review: Secure Range API boundary handling and range-based DOM operations.

### Background
Under Lightning Web Security (LWS), a component shares the top-level document with the rest of the page: the `<html>`, `<head>`, and `<body>` elements are shared and are not owned by any single component. The Range API — including the `AbstractRange` boundary surface it exposes (`startContainer`, `endContainer`, `startOffset`, `endOffset`) — can position a range across those shared elements and then move, remove, clone, wrap, or insert their contents. Because the shared elements do not belong to any single component, range boundaries and range-based DOM operations that reach the shared document are restricted: boundary-setting calls that would include a shared element are prevented, structural range operations refuse to move/remove/clone shared content, `insertNode` permits only a `<script>` or `<link>` directly under a shared element and otherwise throws, and `createContextualFragment` sanitizes the HTML it parses into the shared DOM.

Knowing HOW this is enforced is unnecessary. What matters is recognizing range code that targets the shared/top-level document and will therefore behave differently — or throw — because the nodes are shared.

### Scope
This review identifies Range API code whose correctness depends on positioning a range over, or operating on, the shared/top-level document — `document` itself, `document.documentElement` (the `<html>`), `document.head`, `document.body`, or nodes obtained from them. This covers two surfaces: (1) setting range boundaries onto shared nodes, and (2) running range-based structural DOM operations that move, remove, clone, wrap, or insert content across shared nodes.

### What To Flag

1. **Range boundaries anchored on shared / top-level nodes**
   - `range.setStart(document.body, 0)`, `range.setEnd(document.documentElement, 0)`, `range.setStartBefore(document.head)`, `range.setEndAfter(document.body)`, `range.selectNode(document.body)`, `range.selectNodeContents(document.documentElement)`.
   - Reading `range.startContainer` / `range.endContainer` and expecting to reach or mutate a shared element through it.
   - **Why**: A range boundary is prevented from including a shared element, so these calls do not position the range as written — they are blocked or throw.
   - **Fix**: Confine the range to component-owned nodes — nodes the component itself created or rendered, reached through its own scoped root (e.g. `this.template` in LWC, `this.renderRoot`/`shadowRoot` in Lit, a ref in React); never anchor a boundary on `document`, `<html>`, `<head>`, or `<body>`.

2. **Range-based structural operations across shared nodes**
   - `range.extractContents()`, `range.deleteContents()`, `range.cloneContents()`, `range.surroundContents(node)`, or `range.insertNode(node)` where the range spans — or the node targets — the shared document.
   - **Why**: Moving, removing, or cloning shared content is refused; `insertNode` only permits a `<script>` or `<link>` directly under a shared element and otherwise throws.
   - **Fix**: Run range operations only within the component's own subtree; do not restructure the shared `<html>` / `<head>` / `<body>`.

3. **`createContextualFragment` with untrusted HTML destined for the shared DOM**
   - `range.createContextualFragment(html)` where `html` is untrusted and the resulting fragment is inserted into the shared document.
   - **Why**: HTML parsed into the shared DOM is sanitized, so unsanitized markup will not survive as written.
   - **Fix**: Build DOM with safe, owned APIs (template markup, `createElement` + `textContent`) and keep insertion inside the component.

### What To Ignore
- Range boundaries and range operations confined to component-owned nodes (created locally or reached through the component's own scoped root — `this.template`, `this.renderRoot`/`shadowRoot`, a framework ref, etc.) that never touch `document`, `<html>`, `<head>`, or `<body>`.
- `event.rangeParent` access — that is a distinct event-property concern handled by the "Block UIEvent Range Parent" review. Do NOT flag `rangeParent`.
- Read-only range inspection on component-owned ranges: `range.toString()`, `range.getBoundingClientRect()`, `range.collapsed`, `range.commonAncestorContainer`.
- DOM APIs that are not part of the Range / AbstractRange surface.

### Correct Approach
- Keep every range boundary and range operation inside the component's own DOM subtree.
- Never set a range boundary on — or run extract / delete / clone / surround / insert against — `document`, `document.documentElement`, `document.head`, or `document.body`.
- Treat the shared top-level document as read-only structure; restructure only component-owned nodes.
- Do not rely on `createContextualFragment` to inject untrusted HTML into the shared DOM.
