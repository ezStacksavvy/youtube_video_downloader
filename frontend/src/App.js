import React, { useState, useEffect } from 'react';
import {
  Container, Row, Col, Form, Button, Spinner, Alert,
  Card, Navbar, Nav, Accordion
} from 'react-bootstrap';
import { SunFill, MoonStarsFill } from 'react-bootstrap-icons';
import { Link } from 'react-router-dom';
import './App.css';

// --- IMPORTANT: Paste your Adsterra Direct Link Here ---
const AD_LINK_URL = "https://politicsgrowinghollow.com/hxbkvsvx3q?key=57ca02e3d2bc5896bb2071c9b13a6904";

function App() {
  const [theme, setTheme] = useState('dark');
  const [url, setUrl] = useState('');
  const [videoInfo, setVideoInfo] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [isDownloading, setIsDownloading] = useState({ type: null, quality: null });
  const [unlockStep, setUnlockStep] = useState(0);
  const [countdown, setCountdown] = useState(0);
  const [timerId, setTimerId] = useState(null);
  const [showDownloads, setShowDownloads] = useState(false);

  useEffect(() => {
    document.body.setAttribute('data-bs-theme', theme);
  }, [theme]);

  useEffect(() => {
    if (countdown > 0) {
      const id = setTimeout(() => {
        setCountdown(countdown - 1);
      }, 1000);
      setTimerId(id);
    } else {
      if (timerId) clearTimeout(timerId);
      if (unlockStep === 2) {
        setShowDownloads(true);
      }
    }
    return () => {
      if (timerId) clearTimeout(timerId);
    };
    // eslint-disable-next-line
  }, [countdown, unlockStep]);

  const toggleTheme = () => setTheme(theme === 'dark' ? 'light' : 'dark');

  const handleReset = () => {
    setVideoInfo(null);
    setError('');
    setUrl('');
    setUnlockStep(0);
    setCountdown(0);
    setShowDownloads(false);
    if (timerId) clearTimeout(timerId);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    handleReset();
    if (!url.trim()) {
      setError('Please enter a valid YouTube URL.');
      return;
    }
    setIsLoading(true);
    try {
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5000';
      const response = await fetch(`${apiUrl}/api/get-info`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url }),
      });
      const data = await response.json();
      if (!response.ok || data.error) throw new Error(data.error || 'Failed to fetch video information.');
      setVideoInfo(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleVideoDownload = async (quality) => {
    if (!quality || !videoInfo?.video_id) {
        setError("Could not start download, video information is missing.");
        return;
    };
    setIsDownloading({ type: 'video', quality });
    setError('');
    try {
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5000';
      
      // --- FIX: Send video_id instead of url and title ---
      const response = await fetch(`${apiUrl}/api/process-download`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
            video_id: videoInfo.video_id, 
            quality: quality 
        }),
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.error || 'Download failed on the server.');
      }
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      const contentDisposition = response.headers.get('content-disposition');
      let filename = 'download.mp4';
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="(.+)"/);
        if (filenameMatch && filenameMatch.length > 1) filename = filenameMatch[1];
      }
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(downloadUrl);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsDownloading({ type: null, quality: null });
    }
  };

  const handleUnlockClick = (step) => {
    window.open(AD_LINK_URL, '_blank');
    if (step === 1) {
      setUnlockStep(1);
      setCountdown(5);
    } else if (step === 2) {
      setUnlockStep(2);
      setCountdown(5);
    }
  };
  
  return (
    <>
      <Navbar bg={theme} variant={theme} expand="lg" className="shadow-sm">
        <Container>
          <Navbar.Brand as={Link} to="/" className="fw-bold" onClick={handleReset}>
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="currentColor" className="bi bi-youtube me-2" viewBox="0 0 16 16" style={{ color: '#0d6efd' }}>
              <path d="M8.051 1.999h.089c.822.003 4.987.033 6.11.335a2.01 2.01 0 0 1 1.415 1.42c.101.38.172.883.22 1.402l.01.104.022.26.008.104c.065.914.073 1.77.074 1.957v.075c-.001.188-.01.935-.074 1.957l-.008.104-.022.26-.01.104c-.048.519-.119 1.023-.22 1.402a2.01 2.01 0 0 1-1.415 1.42c-1.16.308-5.569.334-6.18.335h-.142c-.309 0-1.587-.006-2.927-.052l-.17-.006-.087-.004-.171-.007-.171-.007c-1.11-.049-2.167-.128-2.654-.26a2.01 2.01 0 0 1-1.415-1.419c-.111-.417-.185-.986-.235-1.558L.09 9.82l-.008-.104A31 31 0 0 1 0 7.68v-.123c.002-.215.01-.958.064-1.778l.007-.103.003-.052.008-.104.022.26.01-.104c.048-.519.119-1.023.22-1.402a2.01 2.01 0 0 1 1.415-1.42c.487-.13 1.544-.21 2.654-.26l.17-.007.172-.006.086-.003.171-.007A100 100 0 0 1 7.858 2zM6.4 5.209v4.818l4.157-2.408z" />
            </svg>
            Video Downloader
          </Navbar.Brand>
          <Nav>
            <Button variant="outline-secondary" onClick={toggleTheme} className="d-flex align-items-center">
              {theme === 'dark' ? <SunFill /> : <MoonStarsFill />}
              <span className="d-none d-md-inline ms-2">{theme === 'dark' ? 'Light Mode' : 'Dark Mode'}</span>
            </Button>
          </Nav>
        </Container>
      </Navbar>

      <Container fluid className="App" data-bs-theme={theme}>
        <Row className="justify-content-center align-items-center flex-grow-1">
          <Col lg={8}>
            <Card className="text-center main-card">
              <Card.Body>
                <Card.Title as="h2" className="fw-bold mb-3">YouTube Video Downloader</Card.Title>
                <Card.Text className="text-muted mb-4">
                  Paste the video URL, select your desired quality, and download.
                </Card.Text>
                <Form onSubmit={handleSubmit}>
                  <Row className="g-2 justify-content-center">
                    <Col>
                      <Form.Control type="text" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://www.youtube.com/watch?v=..." size="lg" disabled={isLoading} />
                    </Col>
                    <Col xs="auto">
                      <Button variant="primary" type="submit" size="lg" disabled={isLoading} className="px-4">
                        {isLoading ? <Spinner animation="border" size="sm" /> : "Go"}
                      </Button>
                    </Col>
                  </Row>
                </Form>
                {error && <Alert variant="danger" className="mt-4">{error}</Alert>}
              </Card.Body>
            </Card>

            {videoInfo && (
              <Card className="mt-4 results-card">
                <Row g={0}>
                  <Col md={4}>
                    <Card.Img src={videoInfo.thumbnail} className="rounded-start" />
                  </Col>
                  <Col md={8}>
                    <Card.Body>
                      <Card.Title>{videoInfo.title}</Card.Title>
                      {!showDownloads && (
                        <Row className="mt-4 text-center">
                          <Col>
                            <Button variant="danger" size="lg" onClick={() => handleUnlockClick(1)} disabled={unlockStep !== 0}>
                              {unlockStep === 1 ? `Please wait... ${countdown}` : "Unlock Link 1"}
                            </Button>
                          </Col>
                          <Col>
                             <Button variant="danger" size="lg" onClick={() => handleUnlockClick(2)} disabled={unlockStep !== 1 || countdown > 0}>
                              {unlockStep === 2 ? `Please wait... ${countdown}` : "Unlock Link 2"}
                            </Button>
                          </Col>
                        </Row>
                      )}
                      {showDownloads && (
                        <>
                          <div className="mt-3">
                            <h5 className="mb-3">Video (MP4)</h5>
                            <div className="d-flex flex-wrap">
                              {videoInfo.video_formats.map((format, index) => (
                                <Button key={`video-${index}`} variant="outline-primary" className="me-2 mb-2" onClick={() => handleVideoDownload(format.resolution)} disabled={isDownloading.type === 'video'}>
                                  {isDownloading.type === 'video' && isDownloading.quality === format.resolution ? (
                                    <Spinner as="span" animation="border" size="sm" role="status" aria-hidden="true" />
                                  ) : (
                                    `${format.resolution.split('x')[1]}p`
                                  )}
                                </Button>
                              ))}
                            </div>
                          </div>
                          <div className="mt-4">
                            <h5 className="mb-3">Audio Only</h5>
                            <div className="d-flex flex-wrap">
                                {videoInfo.audio_formats.length > 0 ? videoInfo.audio_formats.map((format, index) => (
                                  <Button key={`audio-${index}`} variant="outline-secondary" className="me-2 mb-2" href={format.url} target="_blank" download>
                                    {`${format.quality} (${format.ext.toUpperCase()})`}
                                  </Button>
                                )) : <p className="text-muted">No audio-only formats found.</p>}
                            </div>
                          </div>
                        </>
                      )}
                    </Card.Body>
                  </Col>
                </Row>
              </Card>
            )}

            <Accordion className="mt-5">
              <Accordion.Item eventKey="0">
                <Accordion.Header>How To Use This Tool</Accordion.Header>
                <Accordion.Body>
                  <p><strong>1. Find a Video:</strong> Go to YouTube and copy the URL of the video you want to download.</p>
                  <p><strong>2. Paste the URL:</strong> Paste the copied URL into the input box above and click "Go".</p>
                  <p><strong>3. Unlock Downloads:</strong> Click "Unlock Link 1". A new tab will open. After a 5-second countdown, "Unlock Link 2" will become active. Click it, another tab will open, and after a final 5-second countdown, the download buttons will appear.</p>
                  <p><strong>4. Download:</strong> Click your desired video or audio quality to start the download.</p>
                </Accordion.Body>
              </Accordion.Item>
            </Accordion>
          </Col>
        </Row>
        
        <div className="mt-auto text-center">
          <hr className="w-50 mx-auto" />
          <footer className="text-muted py-3">
            © {new Date().getFullYear()} Video Downloader. All Rights Reserved by DTW ASSET.
          </footer>
        </div>
      </Container>
    </>
  );
}

export default App;