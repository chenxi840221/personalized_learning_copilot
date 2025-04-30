// frontend/src/components/StudentReport.js
import React, { useState, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';
import { uploadReport, getReports, getReport, deleteReport } from '../services/api';

const StudentReport = () => {
  const { user } = useAuth();
  const [reports, setReports] = useState([]);
  const [selectedReport, setSelectedReport] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [reportType, setReportType] = useState('primary');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [filterSchoolYear, setFilterSchoolYear] = useState('');
  const [filterTerm, setFilterTerm] = useState('');
  const [filterReportType, setFilterReportType] = useState('');

  // Fetch reports on component mount
  useEffect(() => {
    if (user) {
      fetchReports();
    }
  }, [user]);

  const fetchReports = async () => {
    setLoading(true);
    try {
      // Build query parameters
      let queryParams = new URLSearchParams();
      if (filterSchoolYear) queryParams.append('school_year', filterSchoolYear);
      if (filterTerm) queryParams.append('term', filterTerm);
      if (filterReportType) queryParams.append('report_type', filterReportType);

      const data = await getReports(queryParams);
      setReports(data);
      setError('');
    } catch (err) {
      setError('Failed to fetch reports. Please try again.');
      console.error('Error fetching reports:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleFileChange = (event) => {
    setSelectedFile(event.target.files[0]);
  };

  const handleReportTypeChange = (event) => {
    setReportType(event.target.value);
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setError('Please select a file to upload');
      return;
    }

    setLoading(true);
    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('report_type', reportType);

      const data = await uploadReport(formData);
      
      // Add the new report to the list and reset form
      setReports([data, ...reports]);
      setSelectedFile(null);
      setError('');
      
      // Reset the file input
      document.getElementById('report-file-input').value = '';
    } catch (err) {
      setError('Failed to upload report. Please try again.');
      console.error('Error uploading report:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleViewReport = async (reportId) => {
    setLoading(true);
    try {
      const data = await getReport(reportId);
      setSelectedReport(data);
      setError('');
    } catch (err) {
      setError('Failed to fetch report details. Please try again.');
      console.error('Error fetching report details:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteReport = async (reportId) => {
    if (!window.confirm('Are you sure you want to delete this report?')) return;

    setLoading(true);
    try {
      await deleteReport(reportId);
      
      // Remove the deleted report from the list
      setReports(reports.filter(report => report.id !== reportId));
      
      // Clear selected report if it was the one deleted
      if (selectedReport && selectedReport.id === reportId) {
        setSelectedReport(null);
      }
      
      setError('');
    } catch (err) {
      setError('Failed to delete report. Please try again.');
      console.error('Error deleting report:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = () => {
    fetchReports();
  };

  const closeReportDetail = () => {
    setSelectedReport(null);
  };

  // Format date for display
  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString();
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold mb-6">Student Reports</h1>
      
      {/* Upload Form */}
      <div className="bg-white rounded-lg shadow-md p-6 mb-8">
        <h2 className="text-xl font-semibold mb-4">Upload New Report</h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Report File (PDF, DOCX, JPG, PNG)
            </label>
            <input
              id="report-file-input"
              type="file"
              onChange={handleFileChange}
              accept=".pdf,.docx,.jpg,.jpeg,.png"
              className="block w-full text-sm text-gray-500
                file:mr-4 file:py-2 file:px-4
                file:rounded-md file:border-0
                file:text-sm file:font-semibold
                file:bg-blue-50 file:text-blue-700
                hover:file:bg-blue-100"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Report Type
            </label>
            <select
              value={reportType}
              onChange={handleReportTypeChange}
              className="mt-1 block w-full py-2 px-3 border border-gray-300 bg-white rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
            >
              <option value="primary">Primary School</option>
              <option value="secondary">Secondary School</option>
              <option value="special_ed">Special Education</option>
              <option value="standardized_test">Standardized Test</option>
            </select>
          </div>
          
          <button
            onClick={handleUpload}
            disabled={loading}
            className="inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
          >
            {loading ? 'Uploading...' : 'Upload Report'}
          </button>
          
          {error && <p className="text-red-500 text-sm mt-2">{error}</p>}
        </div>
      </div>
      
      {/* Filters */}
      <div className="bg-white rounded-lg shadow-md p-6 mb-8">
        <h2 className="text-xl font-semibold mb-4">Filter Reports</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              School Year
            </label>
            <input
              type="text"
              value={filterSchoolYear}
              onChange={(e) => setFilterSchoolYear(e.target.value)}
              placeholder="e.g. 2024-2025"
              className="mt-1 block w-full py-2 px-3 border border-gray-300 bg-white rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Term
            </label>
            <input
              type="text"
              value={filterTerm}
              onChange={(e) => setFilterTerm(e.target.value)}
              placeholder="e.g. Semester 1"
              className="mt-1 block w-full py-2 px-3 border border-gray-300 bg-white rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Report Type
            </label>
            <select
              value={filterReportType}
              onChange={(e) => setFilterReportType(e.target.value)}
              className="mt-1 block w-full py-2 px-3 border border-gray-300 bg-white rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
            >
              <option value="">All Types</option>
              <option value="primary">Primary School</option>
              <option value="secondary">Secondary School</option>
              <option value="special_ed">Special Education</option>
              <option value="standardized_test">Standardized Test</option>
            </select>
          </div>
        </div>
        
        <button
          onClick={handleFilterChange}
          className="mt-4 inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-gray-600 hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500"
        >
          Apply Filters
        </button>
      </div>
      
      {/* Reports List */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-semibold mb-4">Your Reports</h2>
        
        {loading && !selectedReport && (
          <p className="text-gray-500 text-center py-4">Loading reports...</p>
        )}
        
        {!loading && reports.length === 0 && (
          <p className="text-gray-500 text-center py-4">No reports found. Upload your first report above.</p>
        )}
        
        {reports.length > 0 && (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    School
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Year/Term
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Type
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Date
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {reports.map((report) => (
                  <tr key={report.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {report.school_name || 'N/A'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {report.school_year || 'N/A'} 
                      {report.term ? ` / ${report.term}` : ''}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {report.report_type}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {formatDate(report.report_date)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                      <button
                        onClick={() => handleViewReport(report.id)}
                        className="text-blue-600 hover:text-blue-900 mr-3"
                      >
                        View
                      </button>
                      <button
                        onClick={() => handleDeleteReport(report.id)}
                        className="text-red-600 hover:text-red-900"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      
      {/* Report Detail Modal */}
      {selectedReport && (
        <div className="fixed inset-0 overflow-y-auto z-50">
          <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
            <div className="fixed inset-0 transition-opacity" aria-hidden="true">
              <div className="absolute inset-0 bg-gray-500 opacity-75"></div>
            </div>
            
            <span className="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>
            
            <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-5xl sm:w-full">
              <div className="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
                <div className="sm:flex sm:items-start">
                  <div className="mt-3 text-center sm:mt-0 sm:text-left w-full">
                    <h3 className="text-lg leading-6 font-medium text-gray-900">
                      Report Details
                    </h3>
                    
                    <div className="mt-6 space-y-4">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                          <h4 className="text-sm font-medium text-gray-500">School Information</h4>
                          <p className="mt-1">
                            <span className="font-medium">School: </span>
                            {selectedReport.school_name || 'N/A'}
                          </p>
                          <p>
                            <span className="font-medium">Year: </span>
                            {selectedReport.school_year || 'N/A'}
                          </p>
                          <p>
                            <span className="font-medium">Term: </span>
                            {selectedReport.term || 'N/A'}
                          </p>
                          <p>
                            <span className="font-medium">Grade Level: </span>
                            {selectedReport.grade_level || 'N/A'}
                          </p>
                        </div>
                        
                        <div>
                          <h4 className="text-sm font-medium text-gray-500">Report Information</h4>
                          <p className="mt-1">
                            <span className="font-medium">Type: </span>
                            {selectedReport.report_type}
                          </p>
                          <p>
                            <span className="font-medium">Date: </span>
                            {formatDate(selectedReport.report_date)}
                          </p>
                          <p>
                            <span className="font-medium">Teacher: </span>
                            {selectedReport.teacher_name || 'N/A'}
                          </p>
                        </div>
                      </div>
                      
                      {/* Attendance */}
                      {selectedReport.attendance && (
                        <div className="mt-4">
                          <h4 className="text-sm font-medium text-gray-500">Attendance</h4>
                          <div className="mt-1 grid grid-cols-3 gap-4">
                            <div className="text-center p-2 bg-green-50 rounded">
                              <p className="text-xs text-gray-500">Present</p>
                              <p className="text-xl font-bold text-green-600">
                                {selectedReport.attendance.days_present || 0}
                              </p>
                            </div>
                            <div className="text-center p-2 bg-red-50 rounded">
                              <p className="text-xs text-gray-500">Absent</p>
                              <p className="text-xl font-bold text-red-600">
                                {selectedReport.attendance.days_absent || 0}
                              </p>
                            </div>
                            <div className="text-center p-2 bg-yellow-50 rounded">
                              <p className="text-xs text-gray-500">Late</p>
                              <p className="text-xl font-bold text-yellow-600">
                                {selectedReport.attendance.days_late || 0}
                              </p>
                            </div>
                          </div>
                        </div>
                      )}
                      
                      {/* Subjects */}
                      {selectedReport.subjects && selectedReport.subjects.length > 0 && (
                        <div className="mt-4">
                          <h4 className="text-sm font-medium text-gray-500">Subject Performance</h4>
                          <div className="mt-2 overflow-x-auto">
                            <table className="min-w-full divide-y divide-gray-200">
                              <thead className="bg-gray-50">
                                <tr>
                                  <th scope="col" className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Subject
                                  </th>
                                  <th scope="col" className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Grade
                                  </th>
                                  <th scope="col" className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Achievement
                                  </th>
                                </tr>
                              </thead>
                              <tbody className="bg-white divide-y divide-gray-200">
                                {selectedReport.subjects.map((subject, index) => (
                                  <tr key={index} className="hover:bg-gray-50">
                                    <td className="px-4 py-2 whitespace-nowrap text-sm font-medium text-gray-900">
                                      {subject.name}
                                    </td>
                                    <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-500">
                                      {subject.grade || 'N/A'}
                                    </td>
                                    <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-500">
                                      {subject.achievement_level || 'N/A'}
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      )}
                      
                      {/* General Comments */}
                      {selectedReport.general_comments && (
                        <div className="mt-4">
                          <h4 className="text-sm font-medium text-gray-500">General Comments</h4>
                          <div className="mt-1 p-4 bg-gray-50 rounded">
                            <p className="text-sm text-gray-700">
                              {selectedReport.general_comments}
                            </p>
                          </div>
                        </div>
                      )}
                      
                      {/* Document Link */}
                      {selectedReport.document_url && (
                        <div className="mt-4">
                          <h4 className="text-sm font-medium text-gray-500">Original Document</h4>
                          <div className="mt-1">
                            <a 
                              href={selectedReport.document_url} 
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
                            >
                              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                              </svg>
                              View Original Document
                            </a>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
              <div className="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
                <button
                  type="button"
                  onClick={closeReportDetail}
                  className="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default StudentReport;