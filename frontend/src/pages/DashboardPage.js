import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import Modal from '../components/Modal';
import '../styles/Dashboard.css';
import axios from 'axios';

// Import all icons
let mergeIcon, splitIcon, compressIcon, unlockIcon, protectIcon, pdfToWordIcon, wordToPdfIcon;
try {
    mergeIcon = require('../assets/merge.png');
    splitIcon = require('../assets/split.png');
    compressIcon = require('../assets/compress.png');
    unlockIcon = require('../assets/unlock.png');
    protectIcon = require('../assets/protect.png');
    pdfToWordIcon = require('../assets/pdf-to-word.png');
    wordToPdfIcon = require('../assets/word-to-pdf.png');
} catch (e) { console.warn("Could not find all placeholder icons in src/assets/."); }

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

const tools = [
    { name: 'Word to PDF', icon: wordToPdfIcon, accept: {'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx']} },
    { name: 'PDF to Word', icon: pdfToWordIcon, accept: {'application/pdf': ['.pdf']} },
    { name: 'Merge PDF', icon: mergeIcon, accept: {'application/pdf': ['.pdf']} },
    { name: 'Split PDF', icon: splitIcon, accept: {'application/pdf': ['.pdf']} },
    { name: 'Compress PDF', icon: compressIcon, accept: {'application/pdf': ['.pdf']} },
    { name: 'Protect PDF', icon: protectIcon, accept: {'application/pdf': ['.pdf']} }, 
    { name: 'Unlock PDF', icon: unlockIcon, accept: {'application/pdf': ['.pdf']} },
];

function DashboardPage() {
    const [files, setFiles] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState('');
    const [uploadProgress, setUploadProgress] = useState(0);
    const [loadingMessage, setLoadingMessage] = useState('');
    
    // State for modals
    const [isSplitModalVisible, setIsSplitModalVisible] = useState(false);
    const [pageRanges, setPageRanges] = useState('');

    const [isUnlockModalVisible, setIsUnlockModalVisible] = useState(false);
    const [pdfPassword, setPdfPassword] = useState('');

    const [isCompressModalVisible, setIsCompressModalVisible] = useState(false);
    const [compressionLevel, setCompressionLevel] = useState('medium');
    
    const [isProtectModalVisible, setIsProtectModalVisible] = useState(false);
    const [newPdfPassword, setNewPdfPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');

    const [activeTool, setActiveTool] = useState(null);

    const onDrop = useCallback(acceptedFiles => {
        setFiles(prevFiles => [...prevFiles, ...acceptedFiles]);
        setError('');
    }, []);

    const { getRootProps, getInputProps, isDragActive, open } = useDropzone({
        onDrop,
        noClick: true,
        accept: activeTool ? activeTool.accept : undefined,
    });

    const handleToolClick = (tool) => {
        if (tool.disabled) return;
        setFiles([]);
        setError('');
        setActiveTool(tool);
        open();
    };

    const performOperation = async (endpoint, formData, downloadName) => {
        setIsLoading(true);
        setUploadProgress(0);
        setLoadingMessage('Uploading...');
        setError('');
        setIsSplitModalVisible(false);
        setIsUnlockModalVisible(false);
        setIsCompressModalVisible(false);
        setIsProtectModalVisible(false);

        try {
            const token = localStorage.getItem('token');
            const response = await axios.post(`${API_URL}/api/${endpoint}`, formData, {
                headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'multipart/form-data' },
                onUploadProgress: (progressEvent) => {
                    const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
                    setUploadProgress(percentCompleted);
                    if (percentCompleted === 100) setLoadingMessage('Processing your file...');
                },
                responseType: 'blob',
            });

            const url = window.URL.createObjectURL(new Blob([response.data]));
            const a = document.createElement('a');
            a.href = url;
            a.download = downloadName;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);
            
            setFiles([]);
            setPageRanges('');
            setPdfPassword('');
            setNewPdfPassword('');
            setConfirmPassword('');
            setCompressionLevel('medium');
            setActiveTool(null);
        } catch (err) {
            if (err.response && err.response.data) {
                try {
                    const errorBlob = await err.response.data.text();
                    const errorJson = JSON.parse(errorBlob);
                    setError(errorJson.error || 'An unknown error occurred.');
                } catch { setError(err.message || 'An unknown error occurred.'); }
            } else { setError(err.message || 'An unknown error occurred.'); }
        } finally {
            setIsLoading(false);
            setUploadProgress(0);
        }
    };
    
    const handleMerge = () => {
        if (files.length < 2) return setError('Please select at least two PDF files to merge.');
        const formData = new FormData();
        files.forEach(file => formData.append('files', file));
        performOperation('merge', formData, 'merged.pdf');
    };
    const handleSplit = () => {
        if (!pageRanges) return setError('Please enter page ranges.');
        const formData = new FormData();
        formData.append('file', files[0]);
        formData.append('ranges', pageRanges);
        performOperation('split', formData, 'split.pdf');
    };
    const handlePdfToWord = () => {
        const formData = new FormData();
        formData.append('file', files[0]);
        performOperation('pdf-to-word', formData, files[0].name.replace(/\.pdf$/i, '.docx'));
    };
    const handleWordToPdf = () => {
        const formData = new FormData();
        formData.append('file', files[0]);
        performOperation('word-to-pdf', formData, files[0].name.replace(/\.docx$/i, '.pdf'));
    };
    const handleCompress = () => {
        const formData = new FormData();
        formData.append('file', files[0]);
        formData.append('level', compressionLevel);
        performOperation('compress', formData, 'compressed.pdf');
    };
    const handleUnlock = () => {
        if (!pdfPassword) return setError('Password is required.');
        const formData = new FormData();
        formData.append('file', files[0]);
        formData.append('password', pdfPassword);
        performOperation('unlock', formData, 'unlocked.pdf');
    };
    const handleProtect = () => {
        if (!newPdfPassword) return setError('Please enter a password.');
        if (newPdfPassword !== confirmPassword) return setError('Passwords do not match.');
        const formData = new FormData();
        formData.append('file', files[0]);
        formData.append('password', newPdfPassword);
        performOperation('protect', formData, 'protected.pdf');
    };

    const onFilesUploaded = () => {
        if (files.length === 0) return;
        switch (activeTool.name) {
            case 'Merge PDF':       handleMerge(); break;
            case 'Split PDF':       setIsSplitModalVisible(true); break;
            case 'PDF to Word':     handlePdfToWord(); break;
            case 'Word to PDF':     handleWordToPdf(); break;
            case 'Compress PDF':    setIsCompressModalVisible(true); break;
            case 'Unlock PDF':      setIsUnlockModalVisible(true); break;
            case 'Protect PDF':     setIsProtectModalVisible(true); break;
            default:                setError('Selected tool is not implemented yet.');
        }
    };

    const removeFile = (fileName) => setFiles(prevFiles => prevFiles.filter(file => file.name !== fileName));
    const uploadedFilesList = files.map(file => (
        <div key={file.name} className="file-item">
            <span>{file.name} - {(file.size / 1024 / 1024).toFixed(2)} MB</span>
            <button onClick={() => removeFile(file.name)} className="remove-file-btn">&times;</button>
        </div>
    ));

    return (
        <div className="dashboard-container">
            {isLoading && (
                <div className="loading-overlay">
                    <div className="loading-content">
                        <div className="spinner"></div>
                        <p>{loadingMessage}</p>
                        {uploadProgress > 0 && uploadProgress < 100 && (
                            <div className="progress-bar-container">
                                <div className="progress-bar" style={{ width: `${uploadProgress}%` }}>
                                    {uploadProgress}%
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            )}

            <Modal isVisible={isSplitModalVisible} onClose={() => setIsSplitModalVisible(false)}>
                <h2>Split PDF</h2>
                <p>Enter page numbers or ranges (e.g., 1, 3-5, 8)</p>
                <input type="text" className="range-input" value={pageRanges} onChange={e => setPageRanges(e.target.value)} placeholder="e.g., 1-3, 5"/>
                <button onClick={handleSplit} className="modal-action-btn">Split</button>
            </Modal>
            <Modal isVisible={isUnlockModalVisible} onClose={() => setIsUnlockModalVisible(false)}>
                <h2>Unlock PDF</h2>
                <p>This file is password protected. Please enter the password.</p>
                <input type="password" className="range-input" value={pdfPassword} onChange={e => setPdfPassword(e.target.value)} placeholder="Enter password"/>
                <button onClick={handleUnlock} className="modal-action-btn">Unlock</button>
            </Modal>
            <Modal isVisible={isCompressModalVisible} onClose={() => setIsCompressModalVisible(false)}>
                <h2>Compress PDF</h2>
                <p>Select a compression level.</p>
                <div className="compression-options">
                    <div className={`compression-option ${compressionLevel === 'low' ? 'selected' : ''}`} onClick={() => setCompressionLevel('low')}><p>Low</p><span>Larger Size, Best Quality</span></div>
                    <div className={`compression-option ${compressionLevel === 'medium' ? 'selected' : ''}`} onClick={() => setCompressionLevel('medium')}><p>Medium</p><span>Good Balance</span></div>
                    <div className={`compression-option ${compressionLevel === 'high' ? 'selected' : ''}`} onClick={() => setCompressionLevel('high')}><p>High</p><span>Smallest Size, Lower Quality</span></div>
                </div>
                <button onClick={handleCompress} className="modal-action-btn">Compress</button>
            </Modal>
            <Modal isVisible={isProtectModalVisible} onClose={() => setIsProtectModalVisible(false)}>
                <h2>Protect PDF</h2>
                <p>Set a password to encrypt your PDF file.</p>
                <input type="password" className="range-input" value={newPdfPassword} onChange={e => setNewPdfPassword(e.target.value)} placeholder="Enter new password"/>
                <input type="password" className="range-input" value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)} placeholder="Confirm new password"/>
                <button onClick={handleProtect} className="modal-action-btn">Protect</button>
            </Modal>
            
            <div {...getRootProps({ className: `dropzone ${isDragActive ? 'dropzone-active' : ''}` })}>
                <input {...getInputProps()} />
                {!activeTool && <p>Select a tool to get started</p>}
                {activeTool && files.length === 0 && <p>Drag & drop files here, or click to select</p>}
                {files.length > 0 && (
                    <div className="file-list-container">
                        <h4>Selected Files:</h4>
                        {uploadedFilesList}
                        <button onClick={onFilesUploaded} className="modal-action-btn" style={{marginTop: '20px'}}>
                            {activeTool ? `${activeTool.name}` : 'Process Files'}
                        </button>
                    </div>
                )}
            </div>
            {error && <p className="error-message-dashboard">{error}</p>}
            <div className="tools-grid">
                {tools.map(tool => (
                    <div key={tool.name} onClick={() => handleToolClick(tool)} className={`tool-card ${tool.disabled ? 'disabled' : ''}`}>
                        <img src={tool.icon} alt={tool.name} />
                        <p>{tool.name}</p>
                    </div>
                ))}
            </div>
        </div>
    );
}

export default DashboardPage;