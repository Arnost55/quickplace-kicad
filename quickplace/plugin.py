"""KiCad PCB Editor Action Plugin interface."""
import json
from pathlib import Path
from time import perf_counter
import wx
import pcbnew
from .engine import Settings, PlacementError, plan
from .adapter import read_board, apply

PREFS=Path.home()/'AppData'/'Roaming'/'QuickPlace'/'settings.json'


def preferences():
    try:
        data=json.loads(PREFS.read_text(encoding='utf-8'))
        return {k:data[k] for k in ('mode','edge','spacing','budget_ms','optimize_ms') if k in data}
    except (OSError,ValueError,TypeError): return {}


def save(settings):
    PREFS.parent.mkdir(parents=True,exist_ok=True)
    PREFS.write_text(json.dumps(settings.__dict__,indent=2),encoding='utf-8')


class PlacementDialog(wx.Dialog):
    def __init__(self,parent,board):
        super().__init__(parent,title='QuickPlace — PCB auto-placement',size=(470,410))
        self.board=board; self.proposal=None; self.footprints=None; self.warnings=[]
        p=preferences(); panel=wx.Panel(self); root=wx.BoxSizer(wx.VERTICAL)
        self.mode=wx.Choice(panel,choices=['Instant','Optimize']); self.mode.SetSelection(1 if p.get('mode')=='optimize' else 0)
        fields=[('Edge clearance (mm)','edge',p.get('edge',0.5)),('Component spacing (mm)','spacing',p.get('spacing',0.5)),('Instant budget (ms)','budget_ms',p.get('budget_ms',150)),('Maximum optimization time (ms)','optimize_ms',p.get('optimize_ms',500))]
        grid=wx.FlexGridSizer(5,2,8,12); grid.AddGrowableCol(1)
        grid.Add(wx.StaticText(panel,label='Mode'),0,wx.ALIGN_CENTER_VERTICAL); grid.Add(self.mode,1,wx.EXPAND)
        self.fields={}
        for label,key,value in fields:
            grid.Add(wx.StaticText(panel,label=label),0,wx.ALIGN_CENTER_VERTICAL)
            ctrl=wx.TextCtrl(panel,value=str(value)); self.fields[key]=ctrl; grid.Add(ctrl,1,wx.EXPAND)
        root.Add(grid,0,wx.ALL|wx.EXPAND,16)
        root.Add(wx.StaticText(panel,label='Locked and routed footprints stay fixed.'),0,wx.LEFT|wx.RIGHT,16)
        self.status=wx.TextCtrl(panel,style=wx.TE_MULTILINE|wx.TE_READONLY|wx.TE_WORDWRAP)
        root.Add(self.status,1,wx.EXPAND|wx.ALL,16)
        row=wx.BoxSizer(wx.HORIZONTAL)
        now=wx.Button(panel,label='QuickPlace Now'); preview=wx.Button(panel,label='Preview'); self.apply_button=wx.Button(panel,label='Apply'); cancel=wx.Button(panel,label='Cancel')
        self.apply_button.Disable()
        for button in (now,preview,self.apply_button,cancel): row.Add(button,0,wx.RIGHT,7)
        root.Add(row,0,wx.ALIGN_RIGHT|wx.LEFT|wx.RIGHT|wx.BOTTOM,12)
        panel.SetSizer(root)
        now.Bind(wx.EVT_BUTTON,lambda event:self.compute(True))
        preview.Bind(wx.EVT_BUTTON,lambda event:self.compute(False))
        self.apply_button.Bind(wx.EVT_BUTTON,self.commit)
        cancel.Bind(wx.EVT_BUTTON,lambda event:self.EndModal(wx.ID_CANCEL))
        for field in self.fields.values(): field.Bind(wx.EVT_TEXT,self.invalidate)
        self.mode.Bind(wx.EVT_CHOICE,self.invalidate)

    def invalidate(self,event):
        self.proposal=None; self.apply_button.Disable(); event.Skip()

    def settings(self):
        vals={key:float(ctrl.GetValue()) for key,ctrl in self.fields.items()}
        if any(v<0 or v>100000 for v in vals.values()): raise PlacementError('Settings must be between 0 and 100000')
        return Settings(edge=vals['edge'],spacing=vals['spacing'],budget_ms=int(vals['budget_ms']),mode='optimize' if self.mode.GetSelection()==1 else 'instant',optimize_ms=int(vals['optimize_ms']))

    def compute(self,apply_now):
        self.apply_button.Disable()
        try:
            settings=self.settings()
            layout,footprints,warnings=read_board(self.board)
            result=plan(layout,settings)
            self.proposal=result; self.footprints=footprints; self.snapshot={ref:(fp.GetPosition().x,fp.GetPosition().y,fp.GetOrientationDegrees(),fp.IsLocked()) for ref,fp in footprints.items()}; self.warnings=warnings
            save(settings)
            percent=(1-result.score_after/result.score_before)*100 if result.score_before>0 else 0
            self.status.SetValue(f'{len(result.positions)} movable / {len(layout.parts)} total footprints\n{result.elapsed_ms:.1f} ms planning time\nEstimated ratsnest span change: {percent:+.1f}% (heuristic only)\n'+('\n'.join(warnings) if warnings else 'No adapter warnings')+'\nGeometric checks passed; DRC not run. Save a backup before applying; undo is not guaranteed by the Python API.')
            self.apply_button.Enable()
            if apply_now: self.commit(None)
        except (PlacementError,ValueError,TypeError,RuntimeError,OSError) as exc:
            self.status.SetValue('Placement failed; board unchanged.\n'+str(exc))
            self.proposal=None

    def commit(self,event):
        if self.proposal is None: return
        try:
            current,footprints,warnings=read_board(self.board)
            if set(footprints)!=set(self.footprints) or any((fp.GetPosition().x,fp.GetPosition().y,fp.GetOrientationDegrees(),fp.IsLocked())!=self.snapshot[ref] for ref,fp in footprints.items()):
                raise PlacementError('Footprints changed since preview; recalculate placement')
            if wx.MessageBox('Apply these positions? KiCad 10 legacy Python has no guaranteed Undo transaction. Save a backup first.','QuickPlace confirmation',wx.YES_NO|wx.NO_DEFAULT|wx.ICON_WARNING,self)!=wx.YES: return
            apply(self.board,footprints,self.proposal)
            wx.MessageBox('Placement applied. Save your PCB and run KiCad DRC before routing. Geometric checks are not a DRC pass.','QuickPlace',wx.OK|wx.ICON_INFORMATION,self)
            self.EndModal(wx.ID_OK)
        except Exception as exc:
            self.status.SetValue('Could not apply placement: '+str(exc))
            self.apply_button.Disable()


class QuickPlacePlugin(pcbnew.ActionPlugin):
    def defaults(self):
        self.name='QuickPlace Now'
        self.category='Placement'
        self.description='Conservative, connectivity-aware PCB component placement'
        self.show_toolbar_button=True
        self.icon_file_name=str(Path(__file__).with_name('icon.png'))

    def Run(self):
        try:
            board=pcbnew.GetBoard()
            if board is None: raise PlacementError('Open a PCB first')
            dialog=PlacementDialog(None,board)
            try: dialog.ShowModal()
            finally: dialog.Destroy()
        except Exception as exc:
            wx.MessageBox(str(exc),'QuickPlace error',wx.OK|wx.ICON_ERROR)
