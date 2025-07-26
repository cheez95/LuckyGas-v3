// Test script to verify QR scanner integration with DeliveryScanner component
// Run this in the browser console when on the QR scanner page

console.log('Testing QR Scanner Integration...');

// Check if ZXing library is available
if (typeof window.ZXing !== 'undefined') {
    console.log('✅ ZXing library is loaded');
} else {
    console.error('❌ ZXing library is not loaded');
}

// Check if the video element exists
const videoElement = document.querySelector('video');
if (videoElement) {
    console.log('✅ Video element found');
    console.log('Video ready state:', videoElement.readyState);
    console.log('Video dimensions:', videoElement.videoWidth, 'x', videoElement.videoHeight);
} else {
    console.error('❌ Video element not found');
}

// Check if camera stream is active
if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
    navigator.mediaDevices.enumerateDevices()
        .then(devices => {
            const videoDevices = devices.filter(device => device.kind === 'videoinput');
            console.log('📷 Available cameras:', videoDevices.length);
            videoDevices.forEach((device, index) => {
                console.log(`  ${index + 1}. ${device.label || 'Camera ' + (index + 1)}`);
            });
        })
        .catch(err => console.error('Error enumerating devices:', err));
} else {
    console.error('❌ MediaDevices API not available');
}

// Instructions for manual testing
console.log('\n📋 Manual Testing Steps:');
console.log('1. Click "開始掃描" button to start camera');
console.log('2. Open test-qr-code.html on another device/tab');
console.log('3. Point camera at the QR code');
console.log('4. Check console for "QR Code detected" message');
console.log('5. Verify the delivery confirmation is sent via WebSocket');