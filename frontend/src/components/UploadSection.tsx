import { Upload, Card, message, Button } from 'antd';
import { UploadOutlined, FileAddOutlined } from '@ant-design/icons';
import type { UploadProps } from 'antd';

interface UploadSectionProps {
  onUploadSuccess: () => void;
}

export function UploadSection({ onUploadSuccess }: UploadSectionProps) {
  const uploadProps: UploadProps = {
    name: 'file',
    action: '/api/upload',
    accept: '.pdf,.PDF',
    showUploadList: true,
    maxCount: 1,
    onChange(info) {
      if (info.file.status === 'uploading') {
        message.loading({ content: 'Processing PDF...', key: 'upload' });
      }
      if (info.file.status === 'done') {
        message.success({ content: `${info.file.name} processed successfully!`, key: 'upload' });
        onUploadSuccess();
      } else if (info.file.status === 'error') {
        message.error({ content: `${info.file.name} failed to process.`, key: 'upload' });
      }
    },
  };

  return (
    <Card
      title={<><FileAddOutlined /> Upload Data</>}
      size="small"
      style={{ marginTop: 16 }}
    >
      <Upload {...uploadProps}>
        <Button
          icon={<UploadOutlined />}
          block
          type="dashed"
        >
          Upload PDF
        </Button>
      </Upload>
    </Card>
  );
}
