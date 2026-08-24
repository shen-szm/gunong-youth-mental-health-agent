<template>
  <div class="guardian-page">
    <header class="guardian-topbar">
      <RouterLink class="guardian-brand" to="/guardian" aria-label="咕哝守护者工作台首页">
        <span class="guardian-brand-mark">咕</span>
        <span class="guardian-brand-copy"><strong>咕哝守护者</strong><small>青少年心理支持工作台</small></span>
      </RouterLink>
      <nav class="guardian-nav" aria-label="守护者工作台导航">
        <RouterLink to="/guardian/follow-ups">站内回访</RouterLink>
        <RouterLink class="guardian-nav-hide-mobile" to="/">学生陪伴端</RouterLink>
        <RouterLink class="guardian-primary-action" to="/guardian/new">新建工单</RouterLink>
      </nav>
    </header>

    <main>
      <section class="guardian-container guardian-hero">
        <div class="guardian-hero-copy">
          <div class="guardian-status-line">v{{ version }} · 青少年心理支持工作台 · 待专业人员审核</div>
          <h1>把担心，整理成<span>下一步</span></h1>
          <p class="guardian-lead">
            面向家长与教师的多 Agent 支持系统。提交一次去标识化观察后，咕哝会完成安全分流、证据检索、行动方案、资源匹配与站内回访。
          </p>
          <div class="guardian-actions">
            <RouterLink class="guardian-primary-action" to="/guardian/new">开始生成支持方案</RouterLink>
            <a class="guardian-secondary-action" href="#workflow">了解系统如何工作</a>
          </div>
        </div>
        <aside class="guardian-hero-aside" aria-labelledby="guardian-boundary-title">
          <h2 id="guardian-boundary-title">在开始前，请先确认边界</h2>
          <ul class="guardian-boundary-list">
            <li><b>1</b><span><strong>不是诊断工具</strong><br>不输出疾病标签、量表伪分或治疗承诺。</span></li>
            <li><b>2</b><span><strong>只面向成人守护者</strong><br>首版覆盖家长与教师，不直接提供未成年人陪聊。</span></li>
            <li><b>3</b><span><strong>安全规则优先</strong><br>危险信号会终止普通方案并切换到紧急求助路径。</span></li>
          </ul>
          <p class="guardian-boundary-note">所有方案均标记“待专业人员审核”。本工具不能替代持证心理或精神卫生专业人员。</p>
        </aside>
      </section>

      <section class="guardian-emergency-strip" aria-label="紧急求助信息">
        <div><strong>已经出现自伤、服药、明确计划或无法保证安全？</strong><p>不要等待系统生成方案。请让可信成年人陪伴，并立即联系专业或紧急服务。</p></div>
        <div class="guardian-hotlines"><a href="tel:12356">12356 心理援助</a><a href="tel:110">110 报警</a><a href="tel:120">120 急救</a></div>
      </section>

      <section id="workflow" class="guardian-section">
        <div class="guardian-container">
          <div class="guardian-section-header">
            <h2>不是轮流说话，而是一条可审查的任务链</h2>
            <p>每一步都记录状态、结构化结论、证据与降级情况。生成式内容永远不能下调确定性安全规则给出的行动级别。</p>
          </div>
          <div class="guardian-flow">
            <article class="guardian-flow-row"><span>01 · 分流</span><h3>SafetyGate</h3><p>显式危险项、保守语义规则和功能影响共同决定下一步动作；危机路径拥有绝对优先级。</p></article>
            <article class="guardian-flow-row"><span>02 · 并行</span><h3>观察摘要 + 证据 + 资源</h3><p>不使用伪造量表分数；权威资料和东莞白名单独立检索，来源与核验日期可追溯。</p></article>
            <article class="guardian-flow-row"><span>03 · 生成</span><h3>角色化行动方案</h3><p>家长获得家庭沟通和7天行动，教师获得校内观察、最小披露和家校协作建议。</p></article>
            <article class="guardian-flow-row"><span>04 · 复核</span><h3>CrossReviewer</h3><p>检查诊断性措辞、证据覆盖和角色边界；只展示分歧摘要与裁决依据，不展示模型私有思维链。</p></article>
            <article class="guardian-flow-row"><span>05 · 交付</span><h3>PDF + 3/7/15天回访</h3><p>生成带版本、AI标识、证据和适用边界的方案书，并建立可持续跟进的站内回访任务。</p></article>
          </div>
        </div>
      </section>

      <section class="guardian-section alt">
        <div class="guardian-container">
          <div class="guardian-section-header">
            <h2>从一个支持个案开始</h2>
            <p>示范个案不会写入真实姓名、学校、联系方式或精确地址。你仍可在提交前逐项查看和修改。</p>
          </div>
          <div class="guardian-demo-grid">
            <article class="guardian-demo-primary">
              <h3>家长 · 社交退缩与学习变化</h3>
              <p>孩子近期回家后常独处，减少与同伴联系，学习表现下降，已持续约三周。</p>
              <div class="guardian-demo-meta"><span>15–18岁</span><span>持续2–4周</span><span>部分影响日常功能</span></div>
              <RouterLink class="guardian-primary-action" :to="{ path: '/guardian/new', query: { preset: 'parent-watch' } }">使用此个案</RouterLink>
            </article>
            <article class="guardian-demo-secondary">
              <h3>教师 · 到校困难与情绪波动</h3>
              <p>学生近两周迟到增多，课堂参与下降，偶有明显易怒，但没有已知危险信号。</p>
              <div class="guardian-demo-meta"><span>12–14岁</span><span>教师观察</span><span>需要尽快支持</span></div>
              <RouterLink class="guardian-secondary-action" :to="{ path: '/guardian/new', query: { preset: 'teacher-support' } }">使用此个案</RouterLink>
            </article>
          </div>
        </div>
      </section>

      <section class="guardian-section">
        <div class="guardian-container">
          <div class="guardian-section-header">
            <h2>公开产品边界与依据</h2>
            <p>安全策略依据法律、政府公开信息和国际卫生组织指导建立；来源核验不等于临床有效性验证。</p>
          </div>
          <div class="guardian-flow">
            <article class="guardian-flow-row"><span>法律边界</span><h3>精神卫生法</h3><p><a href="https://www.npc.gov.cn/c2/c30834/201905/t20190521_281477.html" target="_blank" rel="noreferrer">查看全国人大公开文本</a></p></article>
            <article class="guardian-flow-row"><span>危机资源</span><h3>12356统一心理援助热线</h3><p><a href="https://www.nhc.gov.cn/yzygj/c100068/202412/49a1a65386cd4be582d4702fd0926ee8.shtml" target="_blank" rel="noreferrer">查看国家卫健委通知</a></p></article>
            <article class="guardian-flow-row"><span>AI治理</span><h3>未成年人和拟人化服务要求</h3><p><a href="https://www.cac.gov.cn/2026-04/10/c_1777558395078289.htm" target="_blank" rel="noreferrer">查看国家网信办公开文本</a></p></article>
          </div>
        </div>
      </section>
    </main>

    <footer class="guardian-footer">咕哝 {{ version }} · AI辅助生成 · 待专业人员审核 · 不收集姓名、学校、电话或精确地址</footer>
  </div>
</template>

<script setup>
const version = import.meta.env.VITE_APP_VERSION || __APP_PACKAGE_VERSION__ || 'local'
</script>
