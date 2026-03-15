import React from 'react';
import ConsequenceSimulator from '@/components/ConsequenceSimulator';
import Layout from '@/components/Layout';

/**
 * Simulator Page
 * 
 * Dedicated page for the Legal Consequence Simulator feature.
 * Allows users to:
 * - Describe planned legal actions
 * - Get automatic mode detection
 * - See legal consequences and risk analysis
 * - View session history
 * 
 * Integrates all Phases 1-4:
 * - Phase 1: Backend consequence analysis
 * - Phase 2: Multilingual detection
 * - Phase 3: Smart mode routing
 * - Phase 4: Database persistence
 */

const Simulator: React.FC = () => {
  return (
    <Layout>
      <main className="flex-grow bg-gradient-to-b from-gray-50 to-white">
        <div className="container mx-auto py-12">
          <ConsequenceSimulator />
        </div>
      </main>
    </Layout>
  );
};

export default Simulator;
