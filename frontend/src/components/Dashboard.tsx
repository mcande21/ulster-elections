import { Layout, Typography, Spin, Alert, Row, Col } from 'antd';
import { useRaces } from '../hooks/useRaces';
import { useFilters } from '../hooks/useFilters';
import { useFilterOptions } from '../hooks/useFilterOptions';
import { FilterSidebar } from './FilterSidebar';
import { StatCards } from './StatCards';
import { RacesTable } from './RacesTable';
import { CompetitivenessChart } from './charts/CompetitivenessChart';
import { CountyChart } from './charts/CountyChart';
import { UploadSection } from './UploadSection';
import { VulnerabilityPanel } from './VulnerabilityPanel';
import { useVulnerabilityScores } from '../hooks/useVulnerabilityScores';

const { Header, Sider, Content } = Layout;
const { Title, Text } = Typography;

export const Dashboard = () => {
  const { filters, updateFilter, clearFilters } = useFilters();
  const { data: races, isLoading, error, refetch } = useRaces(filters);
  const { data: filterOptions } = useFilterOptions();
  const { data: vulnerabilityScores = [], isLoading: isLoadingVulnerability } = useVulnerabilityScores(100, filters);

  if (isLoading && !races) {
    return (
      <Layout style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Spin size="large" tip="What up Brian">
          <div style={{ padding: 50 }} />
        </Spin>
      </Layout>
    );
  }

  if (error) {
    return (
      <Layout style={{ minHeight: '100vh', padding: 24 }}>
        <Alert
          description="Error Loading Data: Failed to load race data. Please try again later."
          type="error"
          showIcon
        />
      </Layout>
    );
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ background: '#fff', padding: '0 24px', boxShadow: '0 2px 8px rgba(0,0,0,0.1)' }}>
        <Title level={2} style={{ margin: '16px 0' }}>Brian's Boards 2025</Title>
        <Text type="secondary">Competitive Race Analysis</Text>
      </Header>

      <Layout>
        <Sider width={280} style={{ background: '#fff', padding: 24 }}>
          <FilterSidebar
            filters={filters}
            onFilterChange={updateFilter}
            onClearFilters={clearFilters}
            filterOptions={filterOptions}
          />
          <UploadSection onUploadSuccess={() => refetch()} />
        </Sider>

        <Content style={{ padding: 24, background: '#f0f2f5' }}>
          <StatCards races={races || []} />

          <div style={{ marginTop: 24 }}>
            <VulnerabilityPanel data={vulnerabilityScores} loading={isLoadingVulnerability} />
          </div>

          <Row gutter={16} style={{ marginTop: 24 }}>
            <Col span={12}>
              <CompetitivenessChart races={races || []} />
            </Col>
            <Col span={12}>
              <CountyChart races={races || []} />
            </Col>
          </Row>

          <div style={{ marginTop: 24 }}>
            <RacesTable races={races || []} />
          </div>
        </Content>
      </Layout>
    </Layout>
  );
};
