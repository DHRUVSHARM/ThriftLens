"use client";

import { Camera, RefreshCcw, RotateCcw, Video, X } from "lucide-react";
import type { PointerEvent } from "react";
import { useCallback, useEffect, useRef, useState } from "react";

import { Button, FieldLabel, IconButton } from "./ui";

const MAX_CAPTURE_EDGE = 1600;
const JPEG_QUALITY = 0.9;

type CaptureState = "ready" | "streaming" | "captured" | "error";
type CropBox = {
  x: number;
  y: number;
  width: number;
  height: number;
};

type CropInteraction = {
  kind: "move" | "resize";
  pointerId: number;
  startClientX: number;
  startClientY: number;
  startBox: CropBox;
  areaWidth: number;
  areaHeight: number;
};

const DEFAULT_CROP_BOX: CropBox = { x: 6, y: 6, width: 88, height: 88 };
const MIN_CROP_SIZE = 18;

type CameraCaptureDialogProps = {
  open: boolean;
  onClose: () => void;
  onCapture: (file: File) => void;
};

export function CameraCaptureDialog({ open, onClose, onCapture }: CameraCaptureDialogProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const cropAreaRef = useRef<HTMLDivElement | null>(null);
  const cropFrameRef = useRef<HTMLDivElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const capturedUrlRef = useRef<string | null>(null);

  const [captureState, setCaptureState] = useState<CaptureState>("ready");
  const [devices, setDevices] = useState<MediaDeviceInfo[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState("");
  const [capturedFile, setCapturedFile] = useState<File | null>(null);
  const [capturedUrl, setCapturedUrl] = useState<string | null>(null);
  const [cropBox, setCropBox] = useState<CropBox>(DEFAULT_CROP_BOX);
  const [cropInteraction, setCropInteraction] = useState<CropInteraction | null>(null);
  const [error, setError] = useState<string | null>(null);

  const clearCapturedPhoto = useCallback(() => {
    if (capturedUrlRef.current) {
      URL.revokeObjectURL(capturedUrlRef.current);
      capturedUrlRef.current = null;
    }
    setCapturedFile(null);
    setCapturedUrl(null);
    setCropBox(DEFAULT_CROP_BOX);
    setCropInteraction(null);
  }, []);

  const stopCamera = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
  }, []);

  const closeDialog = useCallback(() => {
    stopCamera();
    clearCapturedPhoto();
    setError(null);
    setDevices([]);
    setSelectedDeviceId("");
    setCaptureState("ready");
    onClose();
  }, [clearCapturedPhoto, onClose, stopCamera]);

  const startCamera = useCallback(
    async (deviceId?: string) => {
      stopCamera();
      clearCapturedPhoto();
      setError(null);
      setCaptureState("ready");

      if (!navigator.mediaDevices?.getUserMedia) {
        setCaptureState("error");
        setError("Camera capture is not available in this browser. Upload an image instead.");
        return;
      }

      try {
        const video: MediaTrackConstraints = deviceId
          ? { deviceId: { exact: deviceId } }
          : {
              facingMode: { ideal: "environment" },
              width: { ideal: 1280 },
              height: { ideal: 720 },
            };
        const stream = await navigator.mediaDevices.getUserMedia({ audio: false, video });
        streamRef.current = stream;

        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          await videoRef.current.play().catch(() => undefined);
        }

        const videoDevices = navigator.mediaDevices.enumerateDevices
          ? (await navigator.mediaDevices.enumerateDevices()).filter((device) => device.kind === "videoinput")
          : [];
        const activeDeviceId = stream.getVideoTracks()[0]?.getSettings().deviceId || deviceId || "";
        setDevices(videoDevices);
        setSelectedDeviceId(activeDeviceId);
        setCaptureState("streaming");
      } catch (cameraError) {
        stopCamera();
        setCaptureState("error");
        setError(messageForCameraError(cameraError));
      }
    },
    [clearCapturedPhoto, stopCamera],
  );

  useEffect(() => {
    if (!open) return;
    void startCamera();

    return () => {
      stopCamera();
      clearCapturedPhoto();
    };
  }, [clearCapturedPhoto, open, startCamera, stopCamera]);

  useEffect(() => {
    if (!open) return;

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        closeDialog();
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [closeDialog, open]);

  if (!open) {
    return null;
  }

  async function captureFrame() {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || !video.videoWidth || !video.videoHeight) {
      setCaptureState("error");
      setError("Camera preview is not ready yet. Try again in a moment.");
      return;
    }

    const { width, height } = scaledDimensions(video.videoWidth, video.videoHeight);
    canvas.width = width;
    canvas.height = height;
    canvas.getContext("2d")?.drawImage(video, 0, 0, width, height);

    try {
      const blob = await canvasToBlob(canvas);
      const file = new File([blob], `thriftlens-capture-${Date.now()}.jpg`, {
        lastModified: Date.now(),
        type: "image/jpeg",
      });
      const nextUrl = URL.createObjectURL(file);
      clearCapturedPhoto();
      capturedUrlRef.current = nextUrl;
      setCapturedFile(file);
      setCapturedUrl(nextUrl);
      setCaptureState("captured");
      stopCamera();
    } catch {
      setCaptureState("error");
      setError("Camera photo could not be prepared. Retake the photo or upload an image.");
    }
  }

  async function useCapturedPhoto() {
    if (!capturedFile) return;
    try {
      const croppedFile = await cropCapturedFile(capturedFile, cropBox);
      onCapture(croppedFile);
      closeDialog();
    } catch {
      setCaptureState("error");
      setError("Camera crop could not be prepared. Retake the photo or upload an image.");
    }
  }

  function beginCropInteraction(event: PointerEvent, kind: CropInteraction["kind"]) {
    if (!cropAreaRef.current || !cropFrameRef.current) return;
    event.preventDefault();
    event.stopPropagation();
    const areaRect = cropAreaRef.current.getBoundingClientRect();
    cropFrameRef.current.setPointerCapture(event.pointerId);
    setCropInteraction({
      kind,
      pointerId: event.pointerId,
      startClientX: event.clientX,
      startClientY: event.clientY,
      startBox: cropBox,
      areaWidth: areaRect.width,
      areaHeight: areaRect.height,
    });
  }

  function updateCropInteraction(event: PointerEvent) {
    if (!cropInteraction || event.pointerId !== cropInteraction.pointerId) return;
    event.preventDefault();
    const deltaX = ((event.clientX - cropInteraction.startClientX) / cropInteraction.areaWidth) * 100;
    const deltaY = ((event.clientY - cropInteraction.startClientY) / cropInteraction.areaHeight) * 100;

    if (cropInteraction.kind === "move") {
      setCropBox({
        ...cropInteraction.startBox,
        x: clamp(cropInteraction.startBox.x + deltaX, 0, 100 - cropInteraction.startBox.width),
        y: clamp(cropInteraction.startBox.y + deltaY, 0, 100 - cropInteraction.startBox.height),
      });
      return;
    }

    setCropBox({
      x: cropInteraction.startBox.x,
      y: cropInteraction.startBox.y,
      width: clamp(cropInteraction.startBox.width + deltaX, MIN_CROP_SIZE, 100 - cropInteraction.startBox.x),
      height: clamp(cropInteraction.startBox.height + deltaY, MIN_CROP_SIZE, 100 - cropInteraction.startBox.y),
    });
  }

  function endCropInteraction(event: PointerEvent) {
    if (!cropInteraction || event.pointerId !== cropInteraction.pointerId) return;
    cropFrameRef.current?.releasePointerCapture(event.pointerId);
    setCropInteraction(null);
  }

  return (
    <div className="fixed inset-0 z-50 grid place-items-center overflow-x-hidden overflow-y-auto bg-black/60 px-4 py-6" role="presentation">
      <div
        aria-labelledby="camera-capture-title"
        aria-modal="true"
        className="grid max-h-[92vh] w-[calc(100vw-32px)] max-w-[900px] overflow-hidden rounded-lg border border-[var(--border)] bg-[var(--surface)] shadow-[var(--shadow-soft)]"
        role="dialog"
      >
        <div className="flex items-start justify-between gap-4 border-b border-[var(--border)] px-4 py-3">
          <div>
            <h2 id="camera-capture-title" className="text-base font-semibold text-[var(--text-primary)]">
              Camera capture
            </h2>
            <p className="mt-1 text-sm text-[var(--text-secondary)]">Center one product, then use the photo as product evidence.</p>
          </div>
          <IconButton label="Close camera" onClick={closeDialog}>
            <X size={18} aria-hidden="true" />
          </IconButton>
        </div>

        <div className="grid min-w-0 gap-4 overflow-x-hidden overflow-y-auto p-4 md:grid-cols-[minmax(0,1fr)_240px]">
          <div className="relative min-h-[260px] min-w-0 overflow-hidden rounded-lg border border-[var(--border)] bg-black sm:min-h-[300px]">
            {captureState === "captured" && capturedUrl ? (
              <div className="flex h-full min-h-[260px] w-full items-center justify-center p-2 sm:min-h-[300px]">
                <div ref={cropAreaRef} className="relative inline-block max-h-[56vh] max-w-full overflow-hidden">
                  <img alt="Captured product preview" className="block max-h-[56vh] max-w-full select-none object-contain" draggable={false} src={capturedUrl} />
                  <div className="pointer-events-none absolute inset-0 bg-black/35" />
                  <div
                    ref={cropFrameRef}
                    aria-label="Crop frame"
                    className="absolute cursor-move touch-none border border-white bg-transparent shadow-[0_0_0_9999px_rgb(0_0_0_/_0.42)]"
                    role="group"
                    style={{
                      left: `${cropBox.x}%`,
                      top: `${cropBox.y}%`,
                      width: `${cropBox.width}%`,
                      height: `${cropBox.height}%`,
                    }}
                    onPointerCancel={endCropInteraction}
                    onPointerDown={(event) => beginCropInteraction(event, "move")}
                    onPointerMove={updateCropInteraction}
                    onPointerUp={endCropInteraction}
                  >
                    <button
                      aria-label="Resize crop"
                      className="absolute bottom-0 right-0 h-5 w-5 cursor-se-resize rounded-sm border border-white bg-black/75"
                      type="button"
                      onPointerDown={(event) => beginCropInteraction(event, "resize")}
                    />
                  </div>
                </div>
              </div>
            ) : (
              <video
                ref={videoRef}
                className="camera-preview-video h-full max-h-[56vh] min-h-[260px] w-full object-contain sm:min-h-[300px]"
                controlsList="nodownload noplaybackrate noremoteplayback"
                disablePictureInPicture
                muted
                playsInline
              />
            )}
            {captureState === "captured" ? (
              <div className="absolute bottom-3 left-3 rounded-md border border-white/20 bg-black/55 px-2.5 py-1 text-xs font-medium text-white">
                Drag crop frame
              </div>
            ) : null}
            {captureState === "ready" ? (
              <div className="absolute inset-0 grid place-items-center bg-black/55 text-sm text-white">
                <span className="inline-flex items-center gap-2">
                  <Video size={18} aria-hidden="true" />
                  Starting camera...
                </span>
              </div>
            ) : null}
            {captureState === "error" ? (
              <div className="absolute inset-0 grid place-items-center bg-black/70 px-6 text-center text-sm text-white">
                <div>
                  <Camera className="mx-auto mb-3" size={28} aria-hidden="true" />
                  <p>{error}</p>
                </div>
              </div>
            ) : null}
          </div>

          <div className="flex min-w-0 flex-col justify-between gap-4">
            <div className="grid gap-3">
              {captureState === "captured" ? (
                <div className="grid gap-2">
                  <FieldLabel>Crop</FieldLabel>
                  <p className="text-sm leading-6 text-[var(--text-secondary)]">Move the frame and drag the lower-right corner to resize it.</p>
                  <Button type="button" variant="secondary" onClick={() => setCropBox(DEFAULT_CROP_BOX)}>
                    Reset crop
                  </Button>
                </div>
              ) : (
                <>
                  <div className="grid gap-2">
                    <FieldLabel>Camera</FieldLabel>
                    <select
                      aria-label="Camera"
                      className="h-10 w-full rounded-md border border-[var(--border)] bg-[var(--surface-raised)] px-3 text-sm text-[var(--text-primary)] outline-none focus:border-[var(--accent)]"
                      disabled={devices.length <= 1 || captureState !== "streaming"}
                      value={selectedDeviceId}
                      onChange={(event) => void startCamera(event.target.value)}
                    >
                      {devices.length ? (
                        devices.map((device, index) => (
                          <option key={device.deviceId || index} value={device.deviceId}>
                            {device.label || `Camera ${index + 1}`}
                          </option>
                        ))
                      ) : (
                        <option value="">Default camera</option>
                      )}
                    </select>
                  </div>
                  <ul className="grid gap-2 text-sm leading-6 text-[var(--text-secondary)]">
                    <li>Center the product in the frame.</li>
                    <li>Avoid people or crowded scenes.</li>
                    <li>Add a focus note after capture if needed.</li>
                  </ul>
                </>
              )}
            </div>

            <div className="grid gap-2">
              {captureState === "captured" ? (
                <>
                  <Button type="button" variant="primary" onClick={useCapturedPhoto}>
                    <Camera size={18} aria-hidden="true" />
                    Use photo
                  </Button>
                  <Button type="button" variant="secondary" onClick={() => void startCamera(selectedDeviceId || undefined)}>
                    <RefreshCcw size={18} aria-hidden="true" />
                    Retake
                  </Button>
                </>
              ) : (
                <>
                  <Button type="button" variant="primary" disabled={captureState !== "streaming"} onClick={() => void captureFrame()}>
                    <Camera size={18} aria-hidden="true" />
                    Capture photo
                  </Button>
                  <Button type="button" variant="secondary" onClick={() => void startCamera(selectedDeviceId || undefined)}>
                    <RotateCcw size={18} aria-hidden="true" />
                    Restart camera
                  </Button>
                </>
              )}
              <Button type="button" variant="ghost" onClick={closeDialog}>
                Upload instead
              </Button>
            </div>
          </div>
        </div>
        <canvas ref={canvasRef} className="hidden" />
      </div>
    </div>
  );
}

function scaledDimensions(width: number, height: number) {
  const longestEdge = Math.max(width, height);
  if (longestEdge <= MAX_CAPTURE_EDGE) {
    return { width, height };
  }
  const scale = MAX_CAPTURE_EDGE / longestEdge;
  return {
    width: Math.round(width * scale),
    height: Math.round(height * scale),
  };
}

async function cropCapturedFile(file: File, cropBox: CropBox): Promise<File> {
  if (isFullCrop(cropBox)) {
    return file;
  }

  const image = await loadImageForCrop(file);
  try {
    const crop = cropRectForBox(image.width, image.height, cropBox);
    const { width, height } = scaledDimensions(crop.width, crop.height);
    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    canvas
      .getContext("2d")
      ?.drawImage(image.source, crop.x, crop.y, crop.width, crop.height, 0, 0, width, height);

    const blob = await canvasToBlob(canvas);
    return new File([blob], file.name.replace(/\.jpe?g$/i, "-crop.jpg"), {
      lastModified: Date.now(),
      type: "image/jpeg",
    });
  } finally {
    image.close();
  }
}

async function loadImageForCrop(file: File): Promise<{
  source: CanvasImageSource;
  width: number;
  height: number;
  close: () => void;
}> {
  if ("createImageBitmap" in window) {
    const bitmap = await createImageBitmap(file);
    return {
      source: bitmap,
      width: bitmap.width,
      height: bitmap.height,
      close: () => bitmap.close(),
    };
  }

  const objectUrl = URL.createObjectURL(file);
  const image = new Image();
  image.src = objectUrl;
  await image.decode();
  return {
    source: image,
    width: image.naturalWidth,
    height: image.naturalHeight,
    close: () => URL.revokeObjectURL(objectUrl),
  };
}

function cropRectForBox(width: number, height: number, cropBox: CropBox) {
  return {
    x: Math.round((cropBox.x / 100) * width),
    y: Math.round((cropBox.y / 100) * height),
    width: Math.max(1, Math.round((cropBox.width / 100) * width)),
    height: Math.max(1, Math.round((cropBox.height / 100) * height)),
  };
}

function isFullCrop(cropBox: CropBox) {
  return cropBox.x === 0 && cropBox.y === 0 && cropBox.width === 100 && cropBox.height === 100;
}

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}

function canvasToBlob(canvas: HTMLCanvasElement): Promise<Blob> {
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => {
        if (blob) {
          resolve(blob);
        } else {
          reject(new Error("Camera image could not be encoded."));
        }
      },
      "image/jpeg",
      JPEG_QUALITY,
    );
  });
}

function messageForCameraError(error: unknown) {
  if (error instanceof DOMException) {
    if (error.name === "NotAllowedError") {
      return "Camera permission was denied. Allow camera access or upload an image instead.";
    }
    if (error.name === "NotFoundError") {
      return "No camera was found on this device. Upload an image instead.";
    }
    if (error.name === "NotReadableError") {
      return "The camera is already in use or unavailable. Close other camera apps or upload an image.";
    }
  }
  return "Camera capture could not start. Upload an image instead.";
}
