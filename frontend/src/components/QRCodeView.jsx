import { QRCodeSVG } from "qrcode.react";

// The QR code holds only a verification URL with the certificate ID (no personal data).
export default function QRCodeView({ url, size = 150 }) {
  return (
    <figure className="qr">
      <QRCodeSVG value={url} size={size} marginSize={2} />
      <figcaption>Scan to check this certificate's status</figcaption>
    </figure>
  );
}