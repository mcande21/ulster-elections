import { useState } from 'react';
import { Button } from 'antd';
import { DownloadOutlined } from '@ant-design/icons';
import { exportToCSV, exportToPNG } from '../utils/exportUtils';

interface ExportButtonProps {
  // For CSV export
  type: 'csv' | 'png';

  // CSV-specific props
  data?: Record<string, any>[];
  columns?: { key: string; header: string }[];

  // PNG-specific props
  elementRef?: React.RefObject<HTMLElement | null>;

  // Common
  filename: string;
  label?: string;  // Button text, defaults based on type
}

export const ExportButton = ({
  type,
  data,
  columns,
  elementRef,
  filename,
  label
}: ExportButtonProps) => {
  const [loading, setLoading] = useState(false);

  // Determine if button should be disabled
  const isDisabled = type === 'csv'
    ? !data || data.length === 0
    : !elementRef?.current;

  // Default label based on type
  const buttonLabel = label || (type === 'csv' ? 'Export CSV' : 'Export PNG');

  const handleClick = async () => {
    if (type === 'csv') {
      if (!data) {
        console.warn('No data provided for CSV export');
        return;
      }
      exportToCSV(data, filename, columns);
    } else {
      if (!elementRef?.current) {
        console.warn('No element ref provided for PNG export');
        return;
      }

      setLoading(true);
      try {
        await exportToPNG(elementRef.current, filename);
      } catch (error) {
        console.error('PNG export failed:', error);
      } finally {
        setLoading(false);
      }
    }
  };

  return (
    <Button
      icon={<DownloadOutlined />}
      onClick={handleClick}
      disabled={isDisabled}
      loading={loading}
    >
      {buttonLabel}
    </Button>
  );
};
