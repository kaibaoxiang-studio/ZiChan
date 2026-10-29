"""Validate task-local design dimensions without inventing production stages.

The checks bind concrete fields and actual method results. They do not measure
originality or replace the controller's review of the user's design request.
"""
import json

DIMENSIONS = {'face', 'hair', 'skin', 'body', 'costume', 'adornments'}
SPECIALISTS = {
    'face': {'character-face-design'}, 'hair': {'character-hair-design'},
    'skin': {'character-skin-design'}, 'body': {'character-body-design'},
    'costume': {'character-costume-style-design', 'character-costume-cut-design',
                'character-costume-color-design', 'character-costume-material-design'},
    'adornments': {'character-face-signature-design', 'character-costume-accessory-design'},
}


def dimensions(cp, inputs):
    values = inputs.get('requested_dimensions')
    cp.ensure(isinstance(values, list) and values and all(isinstance(x, str) for x in values),
              'Requested design needs actual requested_dimensions')
    cp.ensure(len(values) == len(set(values)) and set(values) <= DIMENSIONS,
              'Unknown or duplicate requested_dimensions')
    return values


def validate_context(cp, inputs, data):
    """Optional production parents are read-only constraints, never approvals."""
    root = None
    if inputs.get('project_root'):
        from pathlib import Path
        root = Path(inputs['project_root']).expanduser().resolve()
        cp.ensure(inputs.get('purpose') == 'candidate', 'Task-local project trial must explicitly have purpose candidate')
        cp.ensure((root / 'project.json').is_file(), 'Design delivery needs a real character project')
        state = cp.read_json(root / 'project.json')
        cp.ensure(state.get('schema_version') == cp.SCHEMA, 'Unsupported project state')
        cp.ensure(not state.get('pending_impact'), 'Resolve upstream impact before design delivery')
        for source in state.get('inputs', {}).values():
            path = root / source['path']
            cp.ensure(path.resolve().is_relative_to(root) and path.is_file() and cp.digest(path) == source['sha256'],
                      'Project source changed or is missing')
        cp.require_text(inputs, 'character_id')
        cp.ensure(inputs['character_id'] in {row['id'] for row in state['roster']}, 'Unknown character ID')
        refs = inputs.get('parent_refs')
        cp.ensure(isinstance(refs, dict) and refs, 'Project trial needs explicit read-only parent_refs')
        cp.ensure(data.get('parent_refs') == refs, 'Trial parent_refs differ from the actual task')
        for key, sha in refs.items():
            record = cp._checked_record(root, state, key)
            cp.ensure(record['sha256'] == sha, f'Trial parent version changed: {key}')
            if key.startswith(('stage-design:', 'design-brief:', 'design-card:')):
                cp.ensure(':' + inputs['character_id'] + ':' in key, 'Trial parent belongs to another character')
    else:
        cp.ensure(not inputs.get('character_id') and not inputs.get('variant_id'),
                  'Standalone task cannot assert a formal asset ID or variant')
        cp.ensure(not inputs.get('parent_refs') and not data.get('parent_refs'),
                  'Standalone design cannot manufacture approved parents')
    return root


def _origin(cp, inputs, data):
    origin = inputs.get('design_origin', 'new')
    cp.ensure(origin in {'new', 'provided', 'captured_from_conversation'}, 'Unknown actual design_origin')
    provenance = data.get('provenance', {})
    cp.ensure(isinstance(provenance, dict), 'Design provenance must be an object')
    cp.ensure(provenance.get('kind', 'new') == origin,
              'Design provenance differs from the actual task')
    if origin != 'new':
        path = provenance.get('source_path')
        if path:
            from pathlib import Path
            canonical = str(Path(path).expanduser().resolve())
            supplied = {str(Path(p).expanduser().resolve()) for p in inputs.get('sources', [])}
            cp.ensure(canonical in supplied, 'Provided/captured design needs its actual original source')
        else:
            original = provenance.get('original_text')
            cp.ensure(isinstance(original, str) and original.strip() and original in inputs['request'],
                      'Conversation capture needs its actual original text in the task or a supplied source')
    return origin


def validate(cp, data, inputs, artifact_root):
    wanted = dimensions(cp, inputs)
    cp.ensure(data.get('requested_dimensions') == wanted, 'Design dimensions differ from the actual task')
    cp.ensure(data.get('scope') == 'requested', 'Requested dimensions are not a production scope')
    cp.ensure(data.get('approved') is not True and not data.get('approval'), 'Task-local design cannot claim formal approval')
    cp.ensure(not any(key in data for key in ('character_id', 'variant_id', 'project_id')),
              'Task-local design must not manufacture production identity')
    validate_context(cp, inputs, data)
    origin = _origin(cp, inputs, data)
    cp.require_text(data, 'design_thesis')
    cp.ensure(isinstance(data.get('understanding'), dict) and data['understanding'],
              'Requested design needs actual character understanding')
    cp.ensure(any(isinstance(value, str) and value.strip() for value in data['understanding'].values()),
              'Character understanding cannot consist only of empty containers')
    for value in data['understanding'].values():
        cp.ensure(isinstance(value, (str, list, dict)), 'Invalid character understanding')
    payload = data.get('payload')
    cp.ensure(isinstance(payload, dict) and payload.get('morphology') in {'human', 'humanoid', 'nonhuman'},
              'Requested design needs a concrete payload and morphology')
    visual = payload.get('visual_details', {})
    cp.ensure(isinstance(visual, dict), 'Requested design needs visual_details')
    cp.ensure(set(visual) <= set(wanted), 'Task-local design changes unrequested visual dimensions')
    human = payload['morphology'] in {'human', 'humanoid'}
    for domain in wanted:
        if human:
            entry = visual.get(domain)
            cp.ensure(isinstance(entry, dict) and entry, f'Requested design missing {domain}')
            fields = cp.DETAIL_FIELDS[domain] if domain != 'adornments' else tuple(entry)
            cp.ensure(bool(fields) and set(entry) <= set(cp.DETAIL_FIELDS[domain]), f'Unknown {domain} fields')
            for field in fields:
                cp.require_text(entry, field)
            if domain == 'body':
                cp.validate_body_form(payload)
                cp.validate_body_proportion_anchors(payload)
        else:
            entry = payload.get('morphology_details', {}).get(domain)
            cp.ensure(isinstance(entry, (str, dict)) and entry, f'Nonhuman design missing current {domain} structure')
    execution = data.get('specialist_execution', {})
    cp.ensure(isinstance(execution, dict), 'Invalid specialist_execution')
    if origin == 'new':
        cp.ensure(execution, 'New design needs actual specialist method results')
    # Only the methods needed by the requested domains run. No thirteen-row
    # plan, default-not-needed receipts or PromptDetailContract are required.
    active = set()
    for specialist, work in execution.items():
        cp.ensure(specialist in cp.SPECIALIST_DOMAINS_V24, 'Unknown specialist')
        cp.ensure(isinstance(work, dict), 'Invalid specialist work')
        cp.require_text(work, 'decision')
        mode = work.get('mode')
        cp.ensure(mode in {'inline', 'independent', 'not_needed'}, 'Unknown specialist execution mode')
        if mode == 'not_needed':
            continue
        active.add(specialist)
        if mode == 'inline':
            cp.ensure(isinstance(work.get('rules_applied'), list) and work['rules_applied'] and
                      all(isinstance(rule, str) and rule.strip() for rule in work['rules_applied']),
                      'Inline work needs the methods actually applied')
            cp.phased._knowledge(cp._runtime(), artifact_root, work.get('knowledge_refs'), specialist, strict=True)
            cp.ensure(isinstance(work.get('results'), list) and work['results'], 'Inline work needs visible results')
            for row in work['results']:
                for field in ('field', 'visible_result', 'basis'):
                    cp.require_text(row, field)
                cp.ensure(row.get('evidence_status') in {'script_fact', 'inference', 'creative_choice'},
                          'Design result needs evidence_status')
                path = row['field'].split('.')
                cp.ensure(len(path) >= 3 and path[0] in ({'visual_details'} if human else {'visual_details', 'morphology_details'}) and
                          path[1] in cp.SPECIALIST_FIELD_DOMAINS[specialist] and path[1] in wanted,
                          'Specialist result belongs to another domain')
                value = cp.phased._get(payload, row['field'])
                if specialist == 'character-feature-focus':
                    cp.ensure(isinstance(value, str) and value.strip(),
                              'Inline focus needs a concrete visible leaf field')
                cp.ensure(row['visible_result'] in (value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)),
                          'Specialist result must actually occur in its adopted design field')
        else:
            focus = specialist == 'character-feature-focus'
            domain = next((d for d in wanted if specialist in SPECIALISTS[d]), None)
            cp.ensure(focus or domain, 'Independent specialist is outside the current task')
            scope = 'body' if domain == 'body' else 'costume' if domain == 'costume' else 'identity'
            proposal = cp.checked_handoff_file(artifact_root, work.get('proposal_ref'), work.get('proposal_sha256'), specialist)
            from validate_specialist_proposal import validate as validate_proposal
            validate_proposal(proposal)
            if focus:
                # A focus consultation may choose anchors across a scope's
                # visible domains, but cannot manufacture a production scope.
                scope = proposal.get('scope')
                cp.ensure(scope in cp.phased.SCOPES,
                          'Independent focus needs a concrete identity/body/costume scope')
                owned = cp.phased.OWNERS[scope] | ({'adornments'} if scope != 'body' else set())
                cp.ensure(owned & set(wanted), 'Independent focus scope is outside the current task')
            cp.ensure(proposal.get('schema_version') == 'CharacterSpecialistProposalV1.2' and
                      proposal.get('specialist') == specialist and proposal.get('scope') == scope and
                      proposal.get('execution_mode') == 'independent' and
                      proposal.get('character_id') == data['subject']['local_key'] and
                      proposal.get('variant_id') == 'base', 'Independent proposal target mismatch')
            cp.phased._knowledge(cp._runtime(), artifact_root, proposal.get('knowledge_refs'), specialist, strict=True)
            option = next((o for o in proposal['options'] if o['id'] == work.get('selected_option_id')), None)
            cp.ensure(option, 'Independent work must select a real proposal option')
            maps = work.get('applied_elements')
            cp.ensure(isinstance(maps, list) and maps, 'Independent work needs applied_elements')
            for mapping in maps:
                cp.ensure(isinstance(mapping, dict), 'Invalid independent element mapping')
                cp.require_text(mapping, 'field')
                index = mapping.get('element_index')
                cp.ensure(isinstance(index, int) and not isinstance(index, bool) and
                          0 <= index < len(option['design_elements']), 'Invalid independent element index')
                parts = mapping['field'].split('.')
                if focus:
                    roots = {'visual_details'} if human else {'visual_details', 'morphology_details'}
                    cp.ensure(len(parts) >= 3 and parts[0] in roots and parts[1] in wanted and
                              parts[1] in cp.SPECIALIST_FIELD_DOMAINS[specialist] and
                              cp.phased._field_scope('visual_details.' + '.'.join(parts[1:])) == scope,
                              'Independent focus result belongs to another scope or domain')
                else:
                    cp.ensure(len(parts) >= 3 and parts[0] == 'visual_details' and
                              parts[1] in cp.SPECIALIST_FIELD_DOMAINS[specialist], 'Independent result belongs to another domain')
                adopted = cp.phased._get(payload, mapping['field'])
                if focus:
                    cp.ensure(isinstance(adopted, str) and adopted.strip(),
                              'Independent focus needs a concrete visible leaf field')
                adopted = adopted if isinstance(adopted, str) else json.dumps(adopted, ensure_ascii=False)
                cp.ensure(all(option['design_elements'][index][f] in adopted for f in
                              ('visible_feature', 'placement_or_structure')), 'Independent result is not adopted')
    if origin == 'new':
        for domain in wanted:
            required = SPECIALISTS[domain]
            if domain == 'adornments':
                cp.ensure(active & required or execution and any(work.get('mode') == 'not_needed' for s, work in execution.items() if s in required),
                          'Adornments need a concrete design or reasoned empty decision')
            else:
                cp.ensure(required <= active, f'Current {domain} design needs actual method results')
    cp.require_list(data, 'unresolved')
    cp.require_list(data, 'deferred_dimensions')
